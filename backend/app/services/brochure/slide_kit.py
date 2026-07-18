"""Low-level python-pptx drawing primitives shared by pptx_generator.py and
one_pager.py — kept separate so neither module reaches into the other's
private helpers.
"""
from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from app.services.brochure.theme import Theme

SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


def color(hex_str: str) -> RGBColor:
    return RGBColor.from_string(hex_str)


def blank_slide(prs: Presentation):
    layout = prs.slide_layouts[6]  # blank layout
    return prs.slides.add_slide(layout)


def fill_background(slide, hex_color: str) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color(hex_color)


def add_rect(slide, left, top, width, height, hex_color: str, line: bool = False):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color(hex_color)
    if not line:
        shape.line.fill.background()
    return shape


def add_text(
    slide,
    left,
    top,
    width,
    height,
    text: str,
    *,
    size: int,
    color_hex: str,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    font_family: str = "Calibri",
    italic: bool = False,
):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font_family
    run.font.color.rgb = color(color_hex)
    return box


def add_bullets(slide, left, top, width, height, items: list[str], *, size: int, color_hex: str, font_family: str):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = f"•  {item}"
        run.font.size = Pt(size)
        run.font.name = font_family
        run.font.color.rgb = color(color_hex)
        p.space_after = Pt(6)
    return box


def eyebrow_and_heading(slide, theme: Theme, eyebrow: str, heading: str, *, dark: bool):
    text_color = theme.text_on_dark_hex if dark else theme.text_on_light_hex
    add_text(
        slide, Inches(0.7), Inches(0.5), Inches(10), Inches(0.5), eyebrow.upper(),
        size=14, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family,
    )
    add_text(
        slide, Inches(0.7), Inches(0.95), Inches(11.5), Inches(1), heading,
        size=32, color_hex=text_color, bold=True, font_family=theme.font_family,
    )


def style_table_header(cell, theme: Theme, text: str) -> None:
    cell.text = text
    cell.text_frame.paragraphs[0].font.bold = True
    cell.text_frame.paragraphs[0].font.size = Pt(11)
    cell.fill.solid()
    cell.fill.fore_color.rgb = color(theme.dark_bg_hex)
    cell.text_frame.paragraphs[0].font.color.rgb = color(theme.text_on_dark_hex)


def style_table_cell(cell, theme: Theme, text: str) -> None:
    cell.text = text
    cell.text_frame.paragraphs[0].font.size = Pt(10.5)
    cell.text_frame.paragraphs[0].font.color.rgb = color(theme.text_on_light_hex)
