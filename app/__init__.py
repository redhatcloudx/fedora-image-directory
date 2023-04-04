"""Main flask application."""
import json
import re

from flask import Flask, render_template
import pandas as pd
import requests

app = Flask("fedora")

# TODO: mhayden Maybe should query https://getfedora.org/releases.json to get latest cloud images.


def load_image_data():
    """Load image data from the image directory."""
    app.logger.info("Loading image data...")
    return pd.read_json("data/images.json.zst")


def current_fedora_releases():
    """Get the latest list of the current Fedora releases."""
    df = pd.read_json("data/releases.json")

    # Reduce the list to only one image per version.
    df = df[(df["variant"] == "Cloud") & df["link"].str.endswith("raw.xz")]

    # Process the image filename.
    regex = r"Fedora-Cloud-Base-(\d+[_]?\w+?-[\dn\.]+\w+)\.raw\.xz"
    df["release"] = df["link"].str.extract(regex, expand=False)

    # Ensure the version contains only the numbers of the release.
    df["version"] = df["release"].str.extract(r"(\d+)", expand=False)

    # Return only the version string and release name.
    return df[["version", "release"]]


def current_fedora_versions():
    """Get the list of current Fedora versions."""
    with open("data/product-versions.json", "r") as fileh:
        versions = json.load(fileh)

    df = pd.DataFrame.from_dict(versions["results"])

    # Pre-release Fedora versions have multiple releases, but stable versions only have
    # one.
    df["prerelease"] = df["releases"].apply(lambda x: True if len(x) > 1 else False)

    return df[["version", "prerelease"]]


def combined_fedora_releases():
    """Join the current versions and releases together."""
    return (
        current_fedora_releases()
        .merge(current_fedora_versions(), on="version")
        .sort_values("version", ascending=False)
    )


def aws_images_for_release(images, release):
    """Get AWS images for a Fedora release."""
    return images[images["Name"].str.contains(release)]


def fedora_images_for_release(df, release):
    """Get the list of images for a given release."""
    return df[df["Name"].str.contains(f"Fedora-Cloud-Base-{release}")]


app.images = load_image_data()


@app.route("/")
def index():
    """Show the main page."""
    return render_template(
        "home.html",
        combined_releases=combined_fedora_releases(),
    )


@app.route("/aws/detail/<release>/")
def aws_image_detail(release):
    """Show the list of AWS images for a given release."""
    return render_template(
        "aws_detail.html",
        release=release,
        images=fedora_images_for_release(app.images, release),
    )


# @app.route("/aws/")
# def aws_image_list(release):
#     """Show the list of AWS images for a given release."""
#     return render_template(
#         "aws.html",
#         release=release,
#         images=fedora_images_for_release(app.images, release),
#     )
