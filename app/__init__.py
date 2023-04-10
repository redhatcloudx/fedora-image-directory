"""Main flask application."""
import json
import re

from flask import Flask, jsonify, render_template, url_for
import pandas as pd
import requests

app = Flask("fedora")

# TODO: mhayden Maybe should query https://getfedora.org/releases.json to get latest cloud images.


def load_image_data():
    """Load image data from the image directory."""
    app.logger.info("Loading image data...")
    return pd.read_json("data/processed.json")


def current_fedora_releases():
    """Get the latest list of the current Fedora releases."""
    df = pd.read_json("data/releases.json")

    # Reduce the list to only one image per version.
    df = df[(df["variant"] == "Cloud") & df["link"].str.endswith("raw.xz")]

    # Remove aarch64 listings to avoid duplication.
    df = df[df["arch"] == "x86_64"]

    # Process the image filename.
    regex = r"Fedora-Cloud-Base-(\d*\w*[_]?\w+?-[\dn\.]+)\.\w+\.raw\.xz"
    df["release"] = df["link"].str.extract(regex, expand=False)

    # Ensure the version contains only the numbers of the release.
    df["version"] = df["release"].str.extract(r"(\d+)", expand=False)

    # Ensure rawhide is capitalized to match the image names.
    df["version"] = df["version"].apply(
        lambda x: x.capitalize() if x == "rawhide" else x
    )

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

    # Ensure rawhide is capitalized to match the image names.
    df["version"] = df["version"].apply(
        lambda x: x.capitalize() if x == "rawhide" else x
    )

    return df[["version", "prerelease"]]


def prerelease_fedora_versions():
    """Get pre-release versions of Fedora in a simple list."""
    return current_fedora_versions().query("prerelease==True")["version"].tolist()


def stable_fedora_versions():
    """Get the latest stable Fedora release."""
    return current_fedora_versions().query("prerelease==False")["version"].tolist()


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
    df = df[df["Name"].str.contains(f"Fedora-Cloud-Base-{release}")]

    # Remove standard storage images.
    df = df[~df["Name"].str.contains("standard")]

    return df.sort_values(["Region", "Architecture"])


def aws_images_all_releases(df):
    """Get a list of Fedora releases from the AWS data."""
    filtered_df = df[df["Name"].str.contains("Fedora-Cloud-Base")].copy(deep=True)

    # Get all of the unique releases from the AWS data.
    # https://regex101.com/r/VtJWa5/1
    regex = r"Fedora-Cloud-Base-(\d*\w*[_]?\w+?-[\dn\.]+)\."
    return filtered_df["Name"].str.extract(regex, expand=False).unique()


app.images = load_image_data()

region_flags = {
    "ap-northeast-1": "jp",
    "ap-northeast-2": "kr",
    "ap-south-1": "in",
    "ap-southeast-1": "sg",
    "ap-southeast-2": "au",
    "ca-central-1": "ca",
    "eu-central-1": "de",
    "eu-west-1": "ie",
    "eu-west-2": "gb",
    "sa-east-1": "br",
    "us-east-1": "us",
    "us-east-2": "us",
    "us-west-1": "us",
    "us-west-2": "us",
}


@app.context_processor
def inject_global_template_variables():
    return dict(fedora_releases=combined_fedora_releases(), region_flags=region_flags)


@app.route("/")
def index():
    """Show the main page."""
    df = app.images
    stable_releases = (
        df[df["fedora.latest_stable"]]
        .sort_values("fedora.release", ascending=False)["fedora.release"]
        .unique()
    )
    return render_template("home.html", stable_releases=stable_releases)


@app.route("/aws/")
def aws_image_list():
    """List all of Fedora releases found in the AWS data."""
    return render_template(
        "aws_list.html",
        releases=aws_images_all_releases(app.images),
        prereleases=prerelease_fedora_versions(),
        all_releases=current_fedora_versions()["version"].tolist(),
        stable_releases=stable_fedora_versions(),
    )


@app.route("/aws/detail/<release>/")
def aws_image_detail(release):
    """Get a list of AWS images for a particular release."""
    return render_template(
        "aws_detail.html",
        release=release,
        images=fedora_images_for_release(app.images, release),
    )


# Routes under this line are for the API.
@app.route("/api/aws/list")
def api_aws_image_list():
    releases = sorted(list(aws_images_all_releases(app.images)), reverse=True)
    return jsonify(
        [
            {
                "release": x,
                "detail_url": url_for(
                    "api_aws_image_detail", release=x, _external=True
                ),
            }
            for x in releases
        ]
    ), {"Content-Type": "application/json; charset=utf-8"}


@app.route("/api/aws/detail/<release>")
def api_aws_image_detail(release):
    images = fedora_images_for_release(app.images, release).to_json(orient="records")
    return jsonify(json.loads(images)), {
        "Content-Type": "application/json; charset=utf-8"
    }
