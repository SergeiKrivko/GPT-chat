# import replicate
#
#
# def extract_text(image: str):
#     return replicate.run(
#         "abiruyt/text-extract-ocr:a524caeaa23495bc9edc805ab08ab5fe943afd3febed884a4f3747aa32e9cd61",
#         input={
#             'image': open(image, 'rb'),
#         },
#     )

import aiohttp

from src.secret_config import OCR_API_KEY


async def extract_text(image: str, lang='eng'):
    with open(image, "rb") as image_file:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.ocr.space/parse/image", data={
                'apikey': OCR_API_KEY,
                'language': lang,
                'file': image_file,
            }) as resp:
                res = await resp.json()
                return res['ParsedResults'][0]['ParsedText']

