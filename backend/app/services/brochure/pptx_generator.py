"""§14 PowerPoint Generator — treated as the primary generation target.

Slide order (§14): Cover → Agenda → Search Profile → Area Overview → Map →
one 3-slide block per Unit (§13: title card / detail page / gallery) →
Comparison → Recommendation → Contact.

PDF is produced from this same deck via LibreOffice headless conversion
(pdf_export.py) — "a flattened export of the same slides," not a second
renderer (§14).
"""
from __future__ import annotations

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from sqlalchemy.orm import Session

from app.models import Client, Proposal, Unit
from app.services.brochure.slide_kit import (
    SLIDE_HEIGHT,
    SLIDE_WIDTH,
    add_bullets,
    add_rect,
    add_text,
    blank_slide,
    color,
    eyebrow_and_heading,
    fill_background,
    style_table_cell,
    style_table_header,
)
from app.services.brochure.theme import DEFAULT_THEME, Theme
from app.services.comparison import ComparisonRow, build_comparison_table
from app.services.qa import QASeverity, run_qa_pass


def _fmt_rate(value: float | None) -> str:
    return f"€{value:,.0f}/m²/yr" if value is not None else "TBD"


# ─────────────────────────────────────────── Slides ───────────────────────────────────────────


def add_cover_slide(prs: Presentation, proposal: Proposal, client: Client, theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.dark_bg_hex)
    add_rect(slide, Inches(0), Inches(6.9), SLIDE_WIDTH, Inches(0.08), theme.accent_hex)

    add_text(slide, Inches(0.9), Inches(1.5), Inches(10), Inches(0.5), "OFFICE SHORTLIST", size=16, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
    add_text(slide, Inches(0.9), Inches(1.95), Inches(11.5), Inches(1.9), proposal.title, size=36, color_hex=theme.text_on_dark_hex, bold=True, font_family=theme.font_family)
    add_text(
        slide, Inches(0.9), Inches(3.95), Inches(10), Inches(0.6),
        "Curated commercial real estate opportunities, assembled for your search.",
        size=16, color_hex=theme.text_on_dark_hex, italic=True, font_family=theme.font_family,
    )
    add_text(slide, Inches(0.9), Inches(5.6), Inches(10), Inches(0.5), f"Prepared exclusively for {client.company_name}", size=18, color_hex=theme.text_on_dark_hex, bold=True, font_family=theme.font_family)
    add_text(slide, Inches(0.9), Inches(6.05), Inches(10), Inches(0.5), f"{len(proposal.selected_units)} locations selected", size=14, color_hex=theme.accent_hex, font_family=theme.font_family)
    return slide


def add_agenda_slide(prs: Presentation, theme: Theme, section_titles: list[str]):
    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)
    eyebrow_and_heading(slide, theme, "Contents", "Agenda", dark=False)
    add_bullets(slide, Inches(0.9), Inches(2.2), Inches(9), Inches(4.5), section_titles, size=18, color_hex=theme.text_on_light_hex, font_family=theme.font_family)
    return slide


def add_search_profile_slide(prs: Presentation, client: Client, theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)
    eyebrow_and_heading(slide, theme, "Client Brief", "Search Profile", dark=False)

    brief = client.search_brief or {}
    budget = brief.get("budget_eur_per_m2_year_max") or brief.get("budget_eur_per_m2_year")
    lines = [
        f"Location: {brief.get('location', 'TBD')}",
        f"Budget: up to €{budget:,.0f}/m²/yr" if budget else "Budget: TBD",
        f"Size: {brief.get('size_m2_min', 'TBD')}–{brief.get('size_m2_max', 'TBD')} m²",
        f"Must-haves: {', '.join(brief.get('must_haves', [])) or 'None specified'}",
    ]
    add_bullets(slide, Inches(0.9), Inches(2.2), Inches(10), Inches(4.5), lines, size=18, color_hex=theme.text_on_light_hex, font_family=theme.font_family)
    return slide


def add_area_overview_slide(prs: Presentation, units: list[Unit], theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)

    neighbourhoods = {u.building.neighbourhood.neighbourhood_id: u.building.neighbourhood for u in units if u.building.neighbourhood}
    eyebrow_and_heading(slide, theme, "Location", "Area Overview", dark=False)

    y = Inches(2.2)
    for nb in neighbourhoods.values():
        add_text(slide, Inches(0.9), y, Inches(10.5), Inches(0.4), nb.name, size=20, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
        y = Inches(y.inches + 0.45)
        if nb.description:
            add_text(slide, Inches(0.9), y, Inches(10.8), Inches(0.7), nb.description, size=13, color_hex=theme.text_on_light_hex, font_family=theme.font_family)
            y = Inches(y.inches + 0.7)
        transit_lines = [f"{t.get('line')} → {t.get('station')} ({t.get('walking_time_min')} min walk)" for t in nb.public_transport]
        if transit_lines:
            add_bullets(slide, Inches(0.9), y, Inches(10.8), Inches(1.2), transit_lines, size=13, color_hex=theme.text_on_light_hex, font_family=theme.font_family)
            y = Inches(y.inches + 0.35 * len(transit_lines) + 0.2)
        y = Inches(y.inches + 0.3)
    return slide


def add_map_slide(prs: Presentation, units: list[Unit], theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)
    eyebrow_and_heading(slide, theme, "Locations", "Map", dark=False)

    placeholder = add_rect(slide, Inches(0.9), Inches(2.1), Inches(11.5), Inches(4.6), "E9E9EC")
    tf = placeholder.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    addresses = ", ".join(sorted({u.building.address for u in units}))
    run.text = f"Interactive map — {addresses}\n(live map tiles require a configured Google Maps / Mapbox key — see app/services/maps.py)"
    run.font.size = Pt(14)
    run.font.color.rgb = color(theme.muted_text_hex)
    return slide


def add_portfolio_overview_slide(prs: Presentation, rows: list[ComparisonRow], theme: Theme):
    """§13 point 2: overview table generated from live Unit data, never hand-typed —
    this is exactly where the source PDF's €55/€60 conflict originated (§1 row 5)."""
    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)
    eyebrow_and_heading(slide, theme, "Portfolio", "Overview", dark=False)

    headers = ["#", "Location", "Floor", "Area (m²)", "Rent €/m²/yr", "Svc Charge €/m²/yr", "Address"]
    table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(0.5), Inches(2.1), Inches(12.3), Inches(4.8))
    table = table_shape.table
    for c, header in enumerate(headers):
        style_table_header(table.cell(0, c), theme, header)

    for r, row in enumerate(rows, start=1):
        values = [
            str(r),
            row.building_name,
            row.floor or "—",
            f"{row.available_area_m2:,.0f}",
            (f"{'from ' if row.rent_price_type == 'from' else ''}€{row.rent_eur_per_m2_year:,.0f}" if row.rent_eur_per_m2_year is not None else "TBD"),
            f"€{row.service_charge_eur_per_m2_year:,.0f}" if row.service_charge_eur_per_m2_year is not None else "TBD",
            row.address,
        ]
        for c, val in enumerate(values):
            style_table_cell(table.cell(r, c), theme, val)
    return slide


def add_unit_title_card_slide(prs: Presentation, index: int, unit: Unit, row: ComparisonRow, theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.dark_bg_hex)
    add_rect(slide, Inches(0), Inches(0), Inches(0.15), SLIDE_HEIGHT, theme.accent_hex)

    add_text(slide, Inches(0.9), Inches(0.6), Inches(2), Inches(0.6), f"{index:02d}", size=36, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
    add_text(slide, Inches(0.9), Inches(1.5), Inches(10), Inches(0.4), "OFFICE FOR LEASE", size=14, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
    add_text(slide, Inches(0.9), Inches(1.95), Inches(11), Inches(0.9), unit.building.name, size=34, color_hex=theme.text_on_dark_hex, bold=True, font_family=theme.font_family)
    neighbourhood_name = unit.building.neighbourhood.name if unit.building.neighbourhood else unit.building.submarket
    add_text(slide, Inches(0.9), Inches(2.75), Inches(11), Inches(0.5), f"{neighbourhood_name} · {unit.building.building_type or 'Office'}", size=16, color_hex=theme.text_on_dark_hex, italic=True, font_family=theme.font_family)
    add_text(slide, Inches(0.9), Inches(3.2), Inches(11), Inches(0.4), unit.building.address, size=14, color_hex=theme.text_on_dark_hex, font_family=theme.font_family)

    rent_label = _fmt_rate(row.rent_eur_per_m2_year)
    if row.rent_price_type == "from" and row.rent_eur_per_m2_year is not None:
        rent_label = f"from {rent_label}"
    stats = [
        ("Area", f"{unit.available_area_m2:,.0f} m²"),
        ("Rent", rent_label),
        ("Service Charge", _fmt_rate(row.service_charge_eur_per_m2_year)),
    ]
    x = Inches(0.9)
    for label, value in stats:
        add_text(slide, x, Inches(5.2), Inches(3.3), Inches(0.4), label.upper(), size=12, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
        add_text(slide, x, Inches(5.6), Inches(3.3), Inches(0.6), value, size=22, color_hex=theme.text_on_dark_hex, bold=True, font_family=theme.font_family)
        x = Inches(x.inches + 3.4)
    return slide


def add_unit_detail_slide(prs: Presentation, unit: Unit, row: ComparisonRow, theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)
    eyebrow_and_heading(slide, theme, unit.building.name, f"{unit.floor or 'Unit'} — Detail", dark=False)

    rent_label = _fmt_rate(row.rent_eur_per_m2_year)
    if row.rent_price_type == "from" and row.rent_eur_per_m2_year is not None:
        rent_label = f"from {rent_label}"
    left_lines = [
        f"Floor Area: {unit.available_area_m2:,.0f} m²" + (f" (divisible from {unit.min_divisible_area_m2:,.0f} m²)" if unit.min_divisible_area_m2 else ""),
        f"Rent: {rent_label}",
        f"Service Charge: {_fmt_rate(row.service_charge_eur_per_m2_year)}",
        f"Contract Term: {unit.contract_term or 'TBD'}",
    ]
    if unit.building.neighbourhood and unit.building.neighbourhood.public_transport:
        for t in unit.building.neighbourhood.public_transport:
            left_lines.append(f"Public Transport: {t.get('line')} → {t.get('station')} ({t.get('walking_time_min')} min)")

    add_text(slide, Inches(0.9), Inches(2.1), Inches(5.5), Inches(0.4), "AT A GLANCE", size=13, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
    add_bullets(slide, Inches(0.9), Inches(2.55), Inches(5.5), Inches(4), left_lines, size=14, color_hex=theme.text_on_light_hex, font_family=theme.font_family)

    right_items = list(unit.unit_amenities or []) + list(unit.building.building_amenities or [])
    add_text(slide, Inches(6.9), Inches(2.1), Inches(5.5), Inches(0.4), "WHAT'S INCLUDED", size=13, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
    add_bullets(slide, Inches(6.9), Inches(2.55), Inches(5.5), Inches(4), right_items or ["Details on request"], size=14, color_hex=theme.text_on_light_hex, font_family=theme.font_family)
    return slide


def add_unit_gallery_slide(prs: Presentation, unit: Unit, theme: Theme):
    from app.services.image_engine import select_gallery

    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)
    eyebrow_and_heading(slide, theme, unit.building.name, "Gallery", dark=False)

    images = select_gallery(unit.photos or unit.building.photos, slots=4)
    positions = [(Inches(0.9), Inches(2.1)), (Inches(6.75), Inches(2.1)), (Inches(0.9), Inches(4.7)), (Inches(6.75), Inches(4.7))]
    for i, (left, top) in enumerate(positions):
        box = add_rect(slide, left, top, Inches(5.6), Inches(2.4), "E9E9EC")
        label = images[i].url_or_path if i < len(images) else "—"
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = label
        run.font.size = Pt(11)
        run.font.color.rgb = color(theme.muted_text_hex)
    return slide


def add_comparison_slide(prs: Presentation, rows: list[ComparisonRow], theme: Theme):
    """§16: computed all-in rate + estimated annual cost, sorted by all-in rate."""
    slide = blank_slide(prs)
    fill_background(slide, theme.light_bg_hex)
    eyebrow_and_heading(slide, theme, "Decision Support", "Comparison", dark=False)

    headers = ["Location", "Floor", "Area (m²)", "All-in €/m²/yr", "Est. Annual Cost", "Energy"]
    table_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(0.5), Inches(2.1), Inches(12.3), Inches(4.8))
    table = table_shape.table
    for c, header in enumerate(headers):
        style_table_header(table.cell(0, c), theme, header)

    for r, row in enumerate(rows, start=1):
        values = [
            row.building_name,
            row.floor or "—",
            f"{row.available_area_m2:,.0f}",
            f"€{row.all_in_rate_eur_per_m2_year:,.0f}" if row.all_in_rate_eur_per_m2_year is not None else "TBD",
            f"€{row.estimated_annual_cost_eur:,.0f}" if row.estimated_annual_cost_eur is not None else "TBD",
            row.energy_label or "—",
        ]
        for c, val in enumerate(values):
            cell = table.cell(r, c)
            style_table_cell(cell, theme, val)
            if c == 3 and r == 1:  # cheapest ready row — rows are pre-sorted ascending by all-in rate
                cell.fill.solid()
                cell.fill.fore_color.rgb = color(theme.accent_hex)
                cell.text_frame.paragraphs[0].font.color.rgb = color(theme.text_on_dark_hex)
                cell.text_frame.paragraphs[0].font.bold = True
    return slide


def add_recommendation_slide(prs: Presentation, rows: list[ComparisonRow], client: Client, theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.dark_bg_hex)
    ready_rows = [r for r in rows if not r.is_tbd]
    top = ready_rows[0] if ready_rows else None

    add_text(slide, Inches(0.9), Inches(0.7), Inches(10), Inches(0.4), "OUR RECOMMENDATION", size=14, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
    if top:
        add_text(slide, Inches(0.9), Inches(1.2), Inches(11), Inches(0.9), f"{top.building_name} — {top.floor or ''}", size=32, color_hex=theme.text_on_dark_hex, bold=True, font_family=theme.font_family)
        reasons = [
            f"Lowest all-in rate of the shortlist at €{top.all_in_rate_eur_per_m2_year:,.0f}/m²/yr",
            f"Estimated annual cost of €{top.estimated_annual_cost_eur:,.0f} for {top.available_area_m2:,.0f} m²",
        ]
        if client.search_brief and client.search_brief.get("must_haves"):
            reasons.append(f"Matches search brief must-haves: {', '.join(client.search_brief['must_haves'])}")
        add_bullets(slide, Inches(0.9), Inches(2.4), Inches(10.5), Inches(3), reasons, size=16, color_hex=theme.text_on_dark_hex, font_family=theme.font_family)
    else:
        add_text(slide, Inches(0.9), Inches(1.2), Inches(11), Inches(1.5), "All shortlisted units are pending final pricing. Recommendation will follow once pricing is confirmed.", size=20, color_hex=theme.text_on_dark_hex, font_family=theme.font_family)
    return slide


def add_contact_slide(prs: Presentation, proposal: Proposal, theme: Theme):
    slide = blank_slide(prs)
    fill_background(slide, theme.dark_bg_hex)
    add_text(slide, Inches(0.9), Inches(2.6), Inches(11), Inches(1), "Questions? We are happy to assist you.", size=30, color_hex=theme.text_on_dark_hex, bold=True, font_family=theme.font_family)
    add_text(slide, Inches(0.9), Inches(3.6), Inches(11), Inches(0.5), proposal.prepared_by or "Your advisor", size=18, color_hex=theme.accent_hex, bold=True, font_family=theme.font_family)
    return slide


# ─────────────────────────────────────────── Orchestration ───────────────────────────────────────────


def build_pptx(db: Session, proposal: Proposal, *, theme: Theme = DEFAULT_THEME, require_qa_pass: bool = True) -> Presentation:
    qa_report = run_qa_pass(db, proposal)
    if require_qa_pass and not qa_report.is_export_ready:
        blocking = [i.message for i in qa_report.issues if i.severity == QASeverity.BLOCKING]
        raise ValueError(
            "Proposal is not export-ready — resolve or explicitly acknowledge these QA issues first "
            f"(§8/§24): {blocking}"
        )

    units = proposal.selected_units
    sorted_rows = build_comparison_table(units)
    row_by_unit_id = {r.unit_id: r for r in sorted_rows}
    rows_in_selection_order = [row_by_unit_id[unit.unit_id] for unit in units]

    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    add_cover_slide(prs, proposal, proposal.client, theme)
    add_agenda_slide(
        prs, theme,
        ["Search Profile", "Area Overview", "Map", "Portfolio Overview", "Property Details", "Comparison", "Recommendation", "Contact"],
    )
    add_search_profile_slide(prs, proposal.client, theme)
    add_area_overview_slide(prs, units, theme)
    add_map_slide(prs, units, theme)
    add_portfolio_overview_slide(prs, rows_in_selection_order, theme)

    for index, unit in enumerate(units, start=1):
        row = row_by_unit_id[unit.unit_id]
        add_unit_title_card_slide(prs, index, unit, row, theme)
        add_unit_detail_slide(prs, unit, row, theme)
        add_unit_gallery_slide(prs, unit, theme)

    add_comparison_slide(prs, sorted_rows, theme)
    add_recommendation_slide(prs, sorted_rows, proposal.client, theme)
    add_contact_slide(prs, proposal, theme)

    return prs
