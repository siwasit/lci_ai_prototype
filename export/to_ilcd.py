"""
export/to_ilcd.py
─────────────────
Export LCIDataset to ILCD-format XML (ISO TS-14048 / ILCD Handbook).
Schema reference: eILCD-SDK_v2.1.1/ILCD/schemas/ILCD_ProcessDataSet.xsd

The produced file is a minimal but valid ILCD processDataSet with:
  - processInformation / dataSetInformation (UUID, name, functional unit)
  - processInformation / quantitativeReference
  - exchanges section (one <exchange> per flow)
"""
from __future__ import annotations
import os, uuid, datetime
from xml.etree import ElementTree as ET
from pipeline.models import LCIDataset
import config

# Namespace map (mirrors the eILCD-SDK example processes)
_NS = {
    "p":    "http://lca.jrc.it/ILCD/Process",
    "c":    "http://lca.jrc.it/ILCD/Common",
    "xsi":  "http://www.w3.org/2001/XMLSchema-instance",
}
_SCHEMA_LOC = (
    "http://lca.jrc.it/ILCD/Process "
    "../../schemas/ILCD_ProcessDataSet.xsd"
)


def _register_namespaces() -> None:
    for prefix, uri in _NS.items():
        ET.register_namespace(prefix, uri)


def _p(tag: str) -> str:
    return f"{{{_NS['p']}}}{tag}"


def _c(tag: str) -> str:
    return f"{{{_NS['c']}}}{tag}"


def export_ilcd(lci: LCIDataset, path: str | None = None) -> str:
    _register_namespaces()

    if path is None:
        os.makedirs(config.DATA_OUTPUT, exist_ok=True)
        safe = lci.process_name.replace(" ", "_").replace(",", "")[:60]
        path = os.path.join(config.DATA_OUTPUT, f"{safe}_ILCD.xml")

    process_uuid = str(uuid.uuid4())
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Root element
    root = ET.Element(
        _p("processDataSet"),
        attrib={
            f"{{{_NS['xsi']}}}schemaLocation": _SCHEMA_LOC,
            "version": "1.1",
        },
    )

    # ── processInformation ──────────────────────────────────────────────
    pi = ET.SubElement(root, _p("processInformation"))

    dsi = ET.SubElement(pi, _p("dataSetInformation"))
    uid_el = ET.SubElement(dsi, _c("UUID"))
    uid_el.text = process_uuid
    name_el = ET.SubElement(dsi, _p("name"))
    bn = ET.SubElement(name_el, _p("baseName"))
    bn.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
    bn.text = lci.process_name
    cl_name = ET.SubElement(name_el, _p("functionalUnitFlowProperties"))
    cl_name.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
    cl_name.text = lci.functional_unit

    geo = ET.SubElement(pi, _p("geography"))
    loc = ET.SubElement(geo, _p("locationOfOperationSupplyOrProduction"))
    loc.set("location", lci.geography if lci.geography else "TH")

    time_el = ET.SubElement(pi, _p("time"))
    ref_yr = ET.SubElement(time_el, _c("referenceYear"))
    ref_yr.text = str(lci.reference_year) if lci.reference_year else "2022"

    tech = ET.SubElement(pi, _p("technology"))
    tt = ET.SubElement(tech, _p("technologyDescriptionAndIncludedProcesses"))
    tt.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
    tt.text = lci.system_boundary

    qref = ET.SubElement(pi, _p("quantitativeReference"))
    qref.set("type", "Reference flow(s)")
    func = ET.SubElement(qref, _p("functionalUnitOrOther"))
    func.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
    func.text = lci.functional_unit

    # ── modellingAndValidation ──────────────────────────────────────────
    mv = ET.SubElement(root, _p("modellingAndValidation"))
    lci_method = ET.SubElement(mv, _p("LCIMethodAndAllocation"))
    mm = ET.SubElement(lci_method, _p("typeOfDataSet"))
    mm.text = "Unit process, single operation"

    # ── administrativeInformation ───────────────────────────────────────
    ai = ET.SubElement(root, _p("administrativeInformation"))
    di = ET.SubElement(ai, _p("dataEntryBy"))
    ts = ET.SubElement(di, _c("timeStamp"))
    ts.text = now

    # ── exchanges ───────────────────────────────────────────────────────
    exchanges = ET.SubElement(root, _p("exchanges"))

    for idx, flow in enumerate(lci.all_flows, start=1):
        ex = ET.SubElement(exchanges, _p("exchange"))
        ex.set("dataSetInternalID", str(idx))

        ref = ET.SubElement(ex, _p("referenceToFlowDataSet"))
        ref.set("type", "flow data set")
        ref.set("uri", f"../flows/{flow.name.replace(' ', '_')}.xml")
        short = ET.SubElement(ref, _c("shortDescription"))
        short.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
        short.text = flow.name

        direction = ET.SubElement(ex, _p("exchangeDirection"))
        direction.text = "Input" if flow.direction == "input" else "Output"

        try:
            amt = float(str(flow.amount).replace(",", ""))
        except (ValueError, TypeError):
            amt = 0.0

        mean_amt = ET.SubElement(ex, _p("meanAmount"))
        mean_amt.text = f"{amt:.6f}"

        result_amt = ET.SubElement(ex, _p("resultingAmount"))
        result_amt.text = f"{amt:.6f}"

        comment = ET.SubElement(ex, _c("generalComment"))
        comment.set("{http://www.w3.org/XML/1998/namespace}lang", "en")
        comment.text = (
            f"Unit: {flow.unit} | Category: {flow.category} | "
            f"Source: {flow.source} | Confidence: {flow.confidence}"
        )

    # ── write ────────────────────────────────────────────────────────────
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, xml_declaration=True, encoding="UTF-8")
    print(f"  [ILCD] → {path}")
    return path
