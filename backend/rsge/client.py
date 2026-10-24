import urllib.request
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ENDPOINT = "https://services.rs.ge/WayBillService/WayBillService.asmx"
NS = "http://tempuri.org/"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
ITYPES = "1,2,3,4,5,6"
STATUSES = "0,1,2,8,-1,-2"


def soap_value(name: str, value: str) -> str:
    return f"<{name}>{escape(value)}</{name}>"


def soap_call(action: str, body: str) -> ET.Element:
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="{SOAP_NS}">
  <soap:Body>
    <{action} xmlns="{NS}">{body}</{action}>
  </soap:Body>
</soap:Envelope>"""
    request = urllib.request.Request(
        ENDPOINT,
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
    result = xml.find(f".//{{{NS}}}{action}Result")
    if result is None:
        raise RuntimeError("Unexpected response from RS.ge:\n" + ET.tostring(xml, encoding="unicode"))
    return result


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
