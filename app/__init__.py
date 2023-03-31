"""Main flask application."""
import re

from flask import Flask, render_template
import pandas as pd

app = Flask("fedora")


def load_image_data():
    """Load image data from the image directory."""
    app.logger.info("Loading image data...")
    return pd.read_json("data/images.json.zst")


def is_official_release(row):
    """Return True if the revision is an official release."""
    if len(row["FedoraRevision"]) >= 8:
        return False

    return True


def filter_fedora_images(version=None):
    """Filter the image data to only include Fedora images.

    https://regex101.com/r/oyOo7A/1

    """
    app.logger.info("Filtering image data...")
    df = app.images[app.images["Name"].str.contains("Fedora-Cloud-Base")]
    regex_string = (
        r"Fedora-Cloud-Base-(\d+[_]?\w+?|Rawhide)-([0-9n\.]+)\."
        r"(\w+)-(\w+)-(\w+-\w+-[0-9]+)-([a-z0-9]+)-(\d)"
    )
    regex = re.compile(regex_string)
    df["FedoraVersion"] = df["Name"].str.extract(regex, expand=False)[0]
    df["FedoraRevision"] = df["Name"].str.extract(regex, expand=False)[1]
    df["FedoraArch"] = df["Name"].str.extract(regex, expand=False)[2]
    df["FedoraVirtType"] = df["Name"].str.extract(regex, expand=False)[3]
    df["FedoraStorage"] = df["Name"].str.extract(regex, expand=False)[5]

    df["Official"] = df.apply(lambda row: is_official_release(row), axis=1)

    if version:
        df = df[df["FedoraVersion"] == version]

    return df.sort_values(["FedoraVersion", "FedoraRevision"], ascending=False)


def fedora_versions():
    """Return a list of Fedora versions."""
    return filter_fedora_images()["FedoraVersion"].unique()


app.images = load_image_data()


@app.route("/")
def index():
    return render_template(
        "index.html", fedora_versions=fedora_versions(), images=filter_fedora_images()
    )


@app.route("/versions/<version>")
def versions(version):
    return render_template(
        "index.html",
        fedora_versions=fedora_versions(),
        images=filter_fedora_images(version),
        current_version=version,
    )
