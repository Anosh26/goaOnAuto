import cv2
import zlib
import re
import numpy as np

def _extract_legacy_xml(xml_string: str) -> dict:
    """Parses legacy Aadhaar XML QR code"""
    data = {}
    
    match = re.search(r'<PrintLetterBarcodeData\s+(.*?)/?>', xml_string, re.IGNORECASE)
    if not match:
        return None
        
    attrs = match.group(1)
    
    # Extract key-value pairs using regex
    # e.g., uid="1234..." name="John Doe"
    attr_pattern = re.findall(r'(\w+)="([^"]*)"', attrs)
    for k, v in attr_pattern:
        data[k.lower()] = v
        
    return {
        "format": "legacy_xml",
        "name": data.get("name", ""),
        "dob": data.get("dob", data.get("yob", "")),
        "gender": data.get("gender", ""),
        "co": data.get("co", ""),
        "house": data.get("house", ""),
        "street": data.get("street", ""),
        "lm": data.get("lm", ""),
        "loc": data.get("loc", ""),
        "vtc": data.get("vtc", ""),
        "po": data.get("po", ""),
        "dist": data.get("dist", ""),
        "subdist": data.get("subdist", ""),
        "state": data.get("state", ""),
        "pc": data.get("pc", "")
    }

def _extract_secure_qr(raw_bytes: bytes) -> dict:
    """Parses Secure e-Aadhaar V2/V3 compressed QR code"""
    try:
        qr_bytes = raw_bytes
        # Check if it's encoded as a Base10 BigInt string (typical for Aadhaar Secure QR)
        try:
            text = raw_bytes.decode('utf-8')
            if text.isdigit() and len(text) > 1000:
                big_int = int(text)
                qr_bytes = big_int.to_bytes((big_int.bit_length() + 7) // 8, byteorder='big')
        except Exception:
            pass

        # Secure QR has ~255 or 256 bytes of signature, followed by the compressed payload
        # Find the gzip magic bytes (1f 8b 08)
        # Some Aadhaar QRs have 256 bytes signature prefix, others are just raw gzip.
        idx = qr_bytes.find(b'\x1f\x8b\x08')
        if idx != -1:
            payload = qr_bytes[idx:]
        else:
            # Fallback to offset 256 if magic bytes not strictly found
            payload = qr_bytes[256:] if len(qr_bytes) > 256 else qr_bytes
        
        # Decompress (Try GZIP, then Auto, then Raw)
        try:
            decompressed = zlib.decompress(payload, wbits=zlib.MAX_WBITS | 16)
        except Exception:
            try:
                decompressed = zlib.decompress(payload, wbits=zlib.MAX_WBITS | 32)
            except Exception:
                decompressed = zlib.decompress(payload, wbits=-zlib.MAX_WBITS)
        
        # The fields are delimited by byte 255 (\xff)
        parts = decompressed.split(b'\xff')
        
        def safe_decode(b):
            try:
                return b.decode('utf-8')
            except:
                try:
                    return b.decode('latin1')
                except:
                    return ""
                    
        return {
            "format": "secure_v2",
            "name": safe_decode(parts[2]) if len(parts) > 2 else "",
            "dob": safe_decode(parts[3]) if len(parts) > 3 else "",
            "gender": safe_decode(parts[4]) if len(parts) > 4 else "",
            "co": safe_decode(parts[5]) if len(parts) > 5 else "",
            "dist": safe_decode(parts[6]) if len(parts) > 6 else "",
            "lm": safe_decode(parts[7]) if len(parts) > 7 else "",
            "house": safe_decode(parts[8]) if len(parts) > 8 else "",
            "loc": safe_decode(parts[9]) if len(parts) > 9 else "",
            "pc": safe_decode(parts[10]) if len(parts) > 10 else "",
            "po": safe_decode(parts[11]) if len(parts) > 11 else "",
            "state": safe_decode(parts[12]) if len(parts) > 12 else "",
            "subdist": safe_decode(parts[13]) if len(parts) > 13 else "",
            "vtc": safe_decode(parts[14]) if len(parts) > 14 else ""
        }
    except Exception as e:
        print(f"Error parsing secure QR: {e}")
        return None

def detect_and_decode_qr(image_path: str):
    """
    Attempts to read Aadhaar QR from the image and extract demographic data.
    """
    img = cv2.imread(image_path)
    if img is None:
        return {"success": False, "error": "Could not read image"}

    raw_data = None
    
    try:
        from pyzbar.pyzbar import decode, ZBarSymbol
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Try raw first
        decoded = decode(gray, symbols=[ZBarSymbol.QRCODE])
        
        # If not found, try CLAHE enhanced
        if not decoded:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            decoded = decode(enhanced, symbols=[ZBarSymbol.QRCODE])
            
        if decoded:
            raw_data = decoded[0].data
    except Exception as e:
        print(f"pyzbar load warning: {e}")
        pass
        
    if not raw_data:
        try:
            import zxingcpp
            results = zxingcpp.read_barcodes(img)
            if results:
                raw_data = results[0].bytes
        except ImportError:
            pass

    if not raw_data:
        # Fallback to OpenCV (Warning: OpenCV returns string, which might corrupt secure QR bytes)
        detector = cv2.QRCodeDetector()
        val, pts, qr_code = detector.detectAndDecode(img)
        if val:
            raw_data = val.encode('utf-8')
            
    if not raw_data:
        return {"success": False, "error": "No QR Code found"}
        
    # Analyze raw data
    try:
        # Check if it's XML (Legacy format)
        decoded_text = raw_data.decode('utf-8').strip()
        if decoded_text.startswith('<?xml') or decoded_text.startswith('<PrintLetterBarcodeData'):
            parsed = _extract_legacy_xml(decoded_text)
            if parsed:
                parsed["success"] = True
                return parsed
    except Exception:
        pass
        
    # If not XML or decoding to utf-8 failed, it's likely Secure QR
    parsed = _extract_secure_qr(raw_data)
    if parsed:
        parsed["success"] = True
        return parsed
        
    return {"success": False, "error": "Found QR but could not parse Aadhaar format"}

if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) > 1:
        res = detect_and_decode_qr(sys.argv[1])
        print(json.dumps(res, indent=2))
