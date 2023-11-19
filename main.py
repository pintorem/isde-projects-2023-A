import json
import io
import base64
from typing import Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import Configuration
from app.forms.classification_form import ClassificationForm
from app.ml.classification_utils import classify_image
from app.ml.classification_utils import fetch_image_bytes
from app.utils import list_images
from PIL import ImageEnhance , Image
from app.forms.classification_transform_form import ClassificationTransformForm
from app.forms.classification_upload_form import ClassificationUploadForm




app = FastAPI()
config = Configuration()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/info")
def info() -> Dict[str, List[str]]:
    """Returns a dictionary with the list of models and
    the list of available image files."""
    list_of_images = list_images()
    list_of_models = Configuration.models
    data = {"models": list_of_models, "images": list_of_images}
    return data


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """The home page of the service."""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/classifications")
def create_classify(request: Request):
    return templates.TemplateResponse(
        "classification_select.html",
        {"request": request, "images": list_images(), "models": Configuration.models},
    )

@app.get("/classificationsTransform")
def create_classify_transform(request: Request):
    """
    This function creates the classification transformation page.
    Parameters
    ----------
    request: Request
        The request that the user sends to the server.

    Returns
    -------
    templates.TemplateResponse
        The classification transformation page.
    """
    return templates.TemplateResponse(
        "classification_transform_select.html",
        {"request": request, "images": list_images(), "models": Configuration.models},
    )

@app.get("/upload-and-classify")
def upload_and_classify(request: Request):
    """
    This function return the upload image page with his form.
    Parameters
    ----------
    request: Request
        The request that the user sends to the server.

    Returns
    -------
    templates.TemplateResponse
        The page with available models and allowed images format    
    """
    return templates.TemplateResponse(
        "classification_upload_image.html",
        {
            "request":request,
            "models": Configuration.models,
            "img_allowed_formats": Configuration.img_allowed_formats
        }
    )

@app.post("/classifications")
async def request_classification(request: Request):
    form = ClassificationForm(request)
    await form.load_data()
    image_id = form.image_id
    model_id = form.model_id
    classification_scores = classify_image(model_id=model_id, img_id=image_id)
    return templates.TemplateResponse(
        "classification_output.html",
        {
            "request": request,
            "image_id": image_id,
            "classification_scores": json.dumps(classification_scores),
        },
    )

@app.post("/upload-and-classify")
async def request_classification_upload(request: Request):
    """
    This function requests the upload image page.
    Parameters
    ----------
    request: Request
        The request that the user sends to the server.

    Returns
    -------
    templates.TemplateResponse
        The page with uploaded classified image and his score.     
    """
    # Load the form data from the post request
    form = ClassificationUploadForm(request)
    await form.load_data()

    if form.is_valid():
        # Retrive image_bytes loaded and model id from the form
        bytes_img = form.image_bytes
        model_id = form.model_id

        # Call classify_image with choosen fetch_image function.
        # fetch_image_bytes allows calling classify_image from raw bytes instead of a file
        classification_scores = classify_image(model_id=model_id, img_id=bytes_img, fetch_image=fetch_image_bytes)

        # Encode the loaded image in base64. It's useful to exploit html <img> tag with src="...;base64= ..."
        b64_img = base64.b64encode(bytes_img).decode('utf-8')
    
        return templates.TemplateResponse(
            "classification_output.html",
            {
                "request": request,
                "image_base64": b64_img,
                "classification_scores": json.dumps(classification_scores),
            },
        )

@app.post("/classificationsTransform")
async def request_classification_transform(request: Request):
    """
    This function requests the classification transformation page.
    Parameters
    ----------
    request: Request
        The request that the user sends to the server.

    Returns
    -------
    templates.TemplateResponse
        The classification transformation page.
        
    """
    form = ClassificationTransformForm(request)
    await form.load_data()
    image_id = form.image_id
    model_id = form.model_id
    color = form.color
    brightness = form.brightness
    contrast = form.contrast
    sharpness = form.sharpness
    with Image.open("app/static/imagenet_subset/" + image_id) as img:
        img = ImageEnhance.Color(img).enhance(color)
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        img = ImageEnhance.Sharpness(img).enhance(sharpness)

        # Save the modified image to a temporary file
        path = "temp.jpg"
        img.save("app/static/imagenet_subset/" + path)

        # Pass the file path to classify_image function
        classification_scores = classify_image(model_id=model_id, img_id=path)

        # Close and delete the temporary file

        return templates.TemplateResponse(
            "classification_output.html",
            {
                "request": request,
                "image_id": path,
                "classification_scores": json.dumps(classification_scores),
            },
        )


