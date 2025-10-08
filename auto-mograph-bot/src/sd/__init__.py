"""Stable Diffusion related interfaces."""

from .txt2img import Txt2ImgGenerator
from .img2vid import Img2VidGenerator

__all__ = ["Txt2ImgGenerator", "Img2VidGenerator"]
