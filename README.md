# fedora-image-directory

Proof of concept Fedora image directory using Cloud Image Directory data

## Data sources

The data in the `data` directory comes from a few different sources:

* `releases.json` comes from [Fedora's website](https://getfedora.org/releases.json)
* `product-versions.json` comes from [Fedora's PDC system](https://pdc.fedoraproject.org/rest_api/v1/product-versions/?active=true&short=fedora)
* `images.json.zst` comes from the [Image Directory](https://imagedirectory.cloud/filtered/aws/owner/125523088429) backend