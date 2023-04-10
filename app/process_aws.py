"""Process Fedora image data from AWS."""
import json

import pandas as pd


def load_raw_image_data():
    """Load image data from the image directory."""
    df = pd.read_json("data/images.json")
    return df[df["Name"].str.startswith("Fedora-Cloud-Base")]


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


def add_fedora_version(df):
    """Add the Fedora version to the dataframe."""
    df["fedora.version"] = df["Name"].str.extract(
        r"Fedora-Cloud-Base-([\d\w]+)", expand=False
    )
    return df


def add_prerelease_flag(df, prerelease_versions):
    """Add the prerelease flag to the dataframe."""
    df["fedora.prerelease"] = df["fedora.version"].apply(
        lambda x: True
        if (x.split("_")[0] in prerelease_versions or "Beta" in x or x == "Rawhide")
        else False
    )
    return df


def add_eol_flag(df, current_versions):
    """Add the EOL flag to the dataframe."""
    non_eol_list = current_versions["version"].to_list()
    df["fedora.eol"] = df["fedora.version"].apply(
        lambda x: False if x.split("_")[0] in non_eol_list else True
    )
    return df


def add_release(df):
    """Add the release name to the dataframe."""
    regex = r"Fedora-Cloud-Base-(\d*\w*[_]?\w+?-[\dn\.]+)\."
    df["fedora.release"] = df["Name"].str.extract(regex, expand=False)
    return df


def add_architecture(df):
    """Add the architecture to the dataframe."""
    df["fedora.architecture"] = df["Name"].apply(
        lambda x: x.split("-")[4].split(".")[-1]
    )
    return df


def add_latest_stable_flag(df, combined_releases):
    """Add the latest stable flag to the dataframe."""
    stable_releases = combined_releases.query("prerelease==False")
    df["fedora.latest_stable"] = df["fedora.release"].apply(
        lambda x: True if x in stable_releases["release"].to_list() else False
    )
    return df


def main():
    """Where the magic happens."""
    fedora_releases = current_fedora_releases()
    fedora_versions = current_fedora_versions()
    combined_releases = combined_fedora_releases()

    # Process the raw image data from AWS.
    aws_images = load_raw_image_data()
    aws_images = add_fedora_version(aws_images)
    aws_images = add_prerelease_flag(aws_images, fedora_versions)
    aws_images = add_eol_flag(aws_images, fedora_versions)
    aws_images = add_release(aws_images)
    aws_images = add_architecture(aws_images)
    aws_images = add_latest_stable_flag(aws_images, combined_releases)

    # Write the processed data to a JSON file.
    aws_images.to_json("data/processed.json", orient="records", indent=2)
