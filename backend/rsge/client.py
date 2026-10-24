import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ENDPOINT = "https://services.rs.ge/WayBillService/WayBillService.asmx"
INVOICE_ENDPOINT = "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
NS = "http://tempuri.org/"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
DIFFGRAM_NS = "urn:schemas-microsoft-com:xml-diffgram-v1"
ITYPES = "1,2,3,4,5,6"
STATUSES = "0,1,2,8,-1,-2"
OPEN_DT_S = "2000-01-01T00:00:00"
OPEN_DT_E = "2100-01-01T00:00:00"


def soap_value(name: str, value: str) -> str:
    return f"<{name}>{escape(value)}</{name}>"


def soap_post(endpoint: str, action: str, body: str) -> ET.Element:
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="{SOAP_NS}">
  <soap:Body>
    <{action} xmlns="{NS}">{body}</{action}>
  </soap:Body>
</soap:Envelope>"""
    request = urllib.request.Request(
        endpoint,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{NS}{action}"',
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        xml = ET.fromstring(response.read())
    fault = xml.find(f".//{{{SOAP_NS}}}Fault")
    if fault is not None:
        raise RuntimeError("SOAP Fault: " + " ".join(fault.itertext()).strip())
    return xml


def soap_call(action: str, body: str) -> ET.Element:
    xml = soap_post(ENDPOINT, action, body)
    result = xml.find(f".//{{{NS}}}{action}Result")
    if result is None:
        raise RuntimeError("Unexpected response from RS.ge:\n" + ET.tostring(xml, encoding="unicode"))
    return result


def invoice_soap_exchange(action: str, body: str) -> ET.Element:
    xml = soap_post(INVOICE_ENDPOINT, action, body)
    response_el = xml.find(f".//{{{NS}}}{action}Response")
    if response_el is None:
        raise RuntimeError("Unexpected response from RS.ge:\n" + ET.tostring(xml, encoding="unicode"))
    return response_el


def invoice_soap_call(action: str, body: str) -> ET.Element:
    response_el = invoice_soap_exchange(action, body)
    result = response_el.find(f"{{{NS}}}{action}Result")
    if result is None:
        raise RuntimeError(
            "Unexpected response from RS.ge:\n" + ET.tostring(response_el, encoding="unicode")
        )
    return result


def response_value(response_el: ET.Element, name: str) -> str:
    value = response_el.findtext(f"{{{NS}}}{name}")
    if value is None or not value.strip():
        raise RuntimeError(
            f"RS.ge response missing {name}\n" + ET.tostring(response_el, encoding="unicode")
        )
    return value.strip()


def result_text(result: ET.Element) -> str:
    parts = []
    if result.text and result.text.strip():
        parts.append(result.text.strip())
    for child in list(result):
        ET.indent(child)
        parts.append(ET.tostring(child, encoding="unicode"))
    return "\n".join(parts)


def call_get_buyer_waybills(su: str, sp: str, create_date_s: str, create_date_e: str) -> ET.Element:
    body = "".join([
        soap_value("su", su),
        soap_value("sp", sp),
        soap_value("itypes", ITYPES),
        soap_value("seller_tin", ""),
        soap_value("statuses", STATUSES),
        soap_value("car_number", ""),
        soap_value("create_date_s", create_date_s),
        soap_value("create_date_e", create_date_e),
        soap_value("driver_tin", ""),
        soap_value("waybill_number", ""),
        soap_value("s_user_ids", ""),
        soap_value("comment", ""),
    ])
    return soap_call("get_buyer_waybills", body)


def call_get_waybill(su: str, sp: str, waybill_id: str) -> ET.Element:
    body = "".join([
        soap_value("su", su),
        soap_value("sp", sp),
        soap_value("waybill_id", waybill_id),
    ])
    return soap_call("get_waybill", body)


def fetch_buyer_waybills(su: str, sp: str, create_date_s: str, create_date_e: str) -> ET.Element:
    result = call_get_buyer_waybills(su, sp, create_date_s, create_date_e)
    if result.find("WAYBILL_LIST") is not None:
        return result
    status = result.find("STATUS")
    detail = result_text(result)
    if status is not None and status.text and int(status.text) < 0:
        raise RuntimeError(
            f"RS.ge get_buyer_waybills STATUS {status.text.strip()} "
            f"for {create_date_s} .. {create_date_e}\n{detail}"
        )
    raise RuntimeError(
        f"Unexpected get_buyer_waybills response for {create_date_s} .. {create_date_e}\n{detail}"
    )


def fetch_waybill_goods(su: str, sp: str, waybill_id: str) -> list[ET.Element]:
    detail = call_get_waybill(su, sp, waybill_id)
    goods = detail.findall(".//GOODS")
    if goods:
        return goods
    status = detail.find("STATUS")
    text = result_text(detail)
    if status is not None and status.text and int(status.text) < 0:
        raise RuntimeError(
            f"RS.ge get_waybill STATUS {status.text.strip()} for waybill {waybill_id}\n{text}"
        )
    raise RuntimeError(f"RS.ge get_waybill {waybill_id} has no GOODS\n{text}")


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def diffgram_rows(result: ET.Element, row_name: str) -> list[ET.Element]:
    diffgram = result.find(f".//{{{DIFFGRAM_NS}}}diffgram")
    if diffgram is None:
        raise RuntimeError("RS.ge response has no diffgram\n" + result_text(result))
    rows = []
    for child in list(diffgram):
        if child.tag in (
            f"{{{DIFFGRAM_NS}}}before",
            f"{{{DIFFGRAM_NS}}}errors",
        ):
            continue
        for row in list(child):
            if local_name(row.tag) == row_name:
                rows.append(row)
    return rows


def negative_status(result: ET.Element) -> str | None:
    status = result.find(".//STATUS")
    if status is None or not status.text or not status.text.strip():
        return None
    text = status.text.strip()
    if int(text) < 0:
        return text
    return None


def call_chek(su: str, sp: str) -> str:
    body = "".join([
        soap_value("su", su),
        soap_value("sp", sp),
        soap_value("user_id", "0"),
    ])
    response_el = invoice_soap_exchange("chek", body)
    ok = response_value(response_el, "chekResult")
    if ok.lower() != "true":
        raise RuntimeError(
            "RS.ge chek rejected the service user\n" + ET.tostring(response_el, encoding="unicode")
        )
    user_id = response_value(response_el, "user_id")
    if int(user_id) <= 0:
        raise RuntimeError(
            f"RS.ge chek returned user_id {user_id}\n" + ET.tostring(response_el, encoding="unicode")
        )
    return user_id


def call_get_un_id(su: str, sp: str, user_id: str) -> str:
    body = "".join([
        soap_value("user_id", user_id),
        soap_value("su", su),
        soap_value("sp", sp),
    ])
    result = invoice_soap_call("get_un_id_from_user_id", body)
    if result.text is None or not result.text.strip():
        raise RuntimeError(
            "RS.ge get_un_id_from_user_id returned no un_id\n" + result_text(result)
        )
    un_id = result.text.strip()
    if int(un_id) <= 0:
        raise RuntimeError(
            f"RS.ge get_un_id_from_user_id returned {un_id}\n" + result_text(result)
        )
    return un_id


def call_get_buyer_invoices(
    su: str,
    sp: str,
    user_id: str,
    un_id: str,
    s_dt: str,
    e_dt: str,
) -> ET.Element:
    body = "".join([
        soap_value("user_id", user_id),
        soap_value("un_id", un_id),
        soap_value("s_dt", s_dt),
        soap_value("e_dt", e_dt),
        soap_value("op_s_dt", OPEN_DT_S),
        soap_value("op_e_dt", OPEN_DT_E),
        soap_value("invoice_no", ""),
        soap_value("sa_ident_no", ""),
        soap_value("desc", ""),
        soap_value("doc_mos_nom", ""),
        soap_value("su", su),
        soap_value("sp", sp),
    ])
    return invoice_soap_call("get_buyer_invoices", body)


def call_get_invoice_desc(su: str, sp: str, user_id: str, invois_id: str) -> ET.Element:
    body = "".join([
        soap_value("user_id", user_id),
        soap_value("invois_id", invois_id),
        soap_value("su", su),
        soap_value("sp", sp),
    ])
    return invoice_soap_call("get_invoice_desc", body)


def fetch_buyer_invoices(
    su: str,
    sp: str,
    user_id: str,
    un_id: str,
    s_dt: str,
    e_dt: str,
) -> list[ET.Element]:
    result = call_get_buyer_invoices(su, sp, user_id, un_id, s_dt, e_dt)
    status = negative_status(result)
    if status is not None:
        raise RuntimeError(
            f"RS.ge get_buyer_invoices STATUS {status} for {s_dt} .. {e_dt}\n" + result_text(result)
        )
    return diffgram_rows(result, "invoices")


def fetch_invoice_lines(su: str, sp: str, user_id: str, invois_id: str) -> list[ET.Element]:
    result = call_get_invoice_desc(su, sp, user_id, invois_id)
    status = negative_status(result)
    if status is not None:
        raise RuntimeError(
            f"RS.ge get_invoice_desc STATUS {status} for {invois_id}\n" + result_text(result)
        )
    return diffgram_rows(result, "invoices_descs")
