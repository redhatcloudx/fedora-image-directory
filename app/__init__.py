"""Main flask application."""
from datetime import datetime
import json
import re

from flask import Flask, jsonify, render_template, url_for
import pandas as pd
import requests

app = Flask("fedora")

# Load the image data into a cache.
app.images = pd.read_json("data/processed.json")

# Translate AWS regions to country flags.
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
    """Inject global template variables into all templates."""
    df = app.images

    # We want the only releases that are marked as the latest stable release. Usually
    # this is current release plus current release minus one, but there are three stable
    # releases for a while as soon as a new release hits GA.
    stable_releases = (
        df[df["fedora_latest_stable"]]
        .sort_values("fedora_release", ascending=False)["fedora_release"]
        .unique()
    )

    # Sometimes we have pre-release versions available, sometimes not.
    prereleases = (
        df[df["fedora_latest_prerelease"]]
        .sort_values("fedora_release", ascending=False)["fedora_release"]
        .unique()
    )

    return dict(
        stable_releases=stable_releases,
        prereleases=prereleases,
        region_flags=region_flags,
        now=datetime.utcnow().strftime("%Y-%m-%d"),
    )


@app.route("/")
def index():
    """Show the main page."""
    return render_template("home.html")


@app.route("/aws/")
def aws_image_list():
    """List all of Fedora releases found in the AWS data."""
    df = app.images

    # Group the results by the release name so we get unique release names and then
    # sort them by the release name while preserving our original index.
    releases = (
        df.query("not fedora_eol and not (fedora_prerelease and fedora_stable)")
        .groupby("fedora_release", as_index=False)
        .first()
        .sort_values(
            ["fedora_stable", "fedora_nightly", "fedora_release"],
            ascending=[False, True, False],
        )
    )

    return render_template(
        "aws_list.html",
        releases=releases.to_dict(orient="records"),
    )


@app.route("/aws/<release>/")
def aws_image_detail(release):
    """Get a list of AWS images for a particular release."""
    df = app.images

    # Filter the data to only include the release we are interested in.
    images = df[df["fedora_release"].str.contains(release)]

    return render_template("aws_regions.html", release=release, images=images)


@app.route("/aws/<release>/<region>/")
def aws_image_per_region(release, region):
    """Get a list of AWS images for a particular release and region."""
    df = app.images

    # Filter the data to only include the release we are interested in.
    images = df[
        (df["fedora_release"] == release) & (df["Region"] == region)
    ].sort_values("Name")

    return render_template(
        "aws_launch.html", release=release, region=region, images=images
    )


# Routes under this line are for the API.
@app.route("/api/aws/releases")
def api_aws_image_list():
    """List all of Fedora releases found in the AWS data."""
    df = app.images

    releases = (
        df.groupby("fedora_release", as_index=False)
        .first()
        .sort_values("fedora_release", ascending=False)
    )

    return releases.to_json(orient="records"), {
        "Content-Type": "application/json; charset=utf-8"
    }


@app.route("/api/aws/images/<release>")
def api_aws_image_detail(release):
    """Get all of the images matching the provided release."""
    df = app.images

    # Filter the data to only include the release we are interested in.
    images = df[df["fedora_release"].str.contains(release)]

    return images.to_json(orient="records"), {
        "Content-Type": "application/json; charset=utf-8"
    }
