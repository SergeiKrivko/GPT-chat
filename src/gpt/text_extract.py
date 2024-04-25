import aiohttp

from src import config


async def extract_text(image: str, lang='eng'):
    with open(image, "rb") as image_file:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.ocr.space/parse/image", data={
                'apikey': config.OCR_API_KEY,
                'language': lang,
                'file': image_file,
            }) as resp:
                res = await resp.json()
                return res['ParsedResults'][0]['ParsedText']
