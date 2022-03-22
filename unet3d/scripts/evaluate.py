import os.path
import glob
from argparse import ArgumentParser
from unet3d.utils.filenames import generate_filenames_from_templates
from unet3d.utils.utils import load_json, load_single_image, get_nibabel_data
import numpy as np
import pandas as pd


def parse_args():
    parser = ArgumentParser(description="Evaluates labelmap volumes against the ground truth. "
                                        "Hierarchical evaluation is not yet supported. "
                                        "Only template filenames are currently supported.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--filenames", nargs="*",
                             help="Assumes filenames start with 'subjectid_' and are labelmaps.")
    input_group.add_argument("--directory",
                             help="Directory where all files in the directory will be evaluated. Assumes the files "
                                  "start with 'subject_id' and are labelmaps.")
    parser.add_argument("--config_filename", required=True)
    parser.add_argument("--output_filename", required=True,
                        help=".csv file to save the results.")
    return parser.parse_args()


def get_filenames(namespace):
    if namespace.filenames:
        return namespace.filenames
    else:
        return glob.glob(os.path.join(namespace.directory, "*"))


def evaluate_filenames(filename1, filename2, labels):
    image1 = load_single_image(filename1, reorder=False)
    data1 = get_nibabel_data(image1)
    image2 = load_single_image(filename2, reorder=False)
    data2 = get_nibabel_data(image2)
    assert np.all(image1.affine == image2.affine)
    return evaluate_image_data(data1, data2, labels)


def evaluate_image_data(data1, data2, labels):
    scores = list()
    for label in labels:
        scores.append(compute_dice(data1 == int(label), data2 == int(label)))
    return scores


def compute_dice(pred, truth):
    return (2 * (pred * truth).sum()) / (pred.sum() + truth.sum())


def main():
    namespace = parse_args()
    config = load_json(namespace.config_filename)
    filenames = get_filenames(namespace)
    subject_ids = list()
    for filename in filenames:
        subject_id = os.path.basename(filename).split("_")[0]
        subject_ids.append(subject_id)

    orig_filenames = generate_filenames_from_templates(subject_ids, skip_targets=False, raise_if_not_exists=True,
                                                       **config["generate_filenames_kwargs"])

    scores = list()
    for i, filename in enumerate(filenames):
        target_filename = orig_filenames[i][-1]
        scores.append(evaluate_filenames(filename, target_filename, labels=config["labels"]))

    df = pd.DataFrame(scores, columns=config["labels"], index=subject_ids)
    df.to_csv(namespace.output_filename)


if __name__ == "__main__":
    main()
