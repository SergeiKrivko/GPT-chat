import replicate


def extract_text(image: str):
    return replicate.run(
        "abiruyt/text-extract-ocr:a524caeaa23495bc9edc805ab08ab5fe943afd3febed884a4f3747aa32e9cd61",
        input={
            'image': open(image, 'rb'),
        },
    )
