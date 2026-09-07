"""
GoaOnAuto QR Code Generator Utility.
Generates standard QR codes (text/URLs) or synthetic Aadhaar QR codes for pipeline testing.
Powered by OpenCV QRCodeEncoder (no external dependencies required).
"""
import os
import sys
import argparse
import cv2

def generate_qr_image(data: str, out_path: str = "generated_qr.png", size: int = 512, border: int = 40) -> str:
    """Encodes string data into a high-contrast QR code image with white border."""
    encoder = cv2.QRCodeEncoder_create()
    qr_matrix = encoder.encode(data)
    if qr_matrix is None or qr_matrix.size == 0:
        raise ValueError("Failed to encode data into QR code.")

    # Scale with nearest neighbor for crisp pixel edges
    scaled = cv2.resize(qr_matrix, (size, size), interpolation=cv2.INTER_NEAREST)
    bordered = cv2.copyMakeBorder(scaled, border, border, border, border, cv2.BORDER_CONSTANT, value=[255, 255, 255])

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cv2.imwrite(out_path, bordered)
    return os.path.abspath(out_path)

def generate_aadhaar_xml(
    name: str = "Applicant Name",
    dob: str = "01/01/2000",
    gender: str = "M",
    careof: str = "S/O Parent Name",
    house: str = "H.No. 100",
    street: str = "Near Temple",
    loc: str = "Village",
    vtc: str = "Mapusa",
    subdist: str = "Bardez",
    dist: str = "North Goa",
    state: str = "Goa",
    pincode: str = "403507",
    uid: str = "987654321012"
) -> str:
    """Generates standard Aadhaar XML string structure."""
    yob = dob.split("/")[-1] if "/" in dob else dob.split("-")[-1]
    xml = (
        f'<PrintLetterBarcodeData uid="{uid}" name="{name}" gender="{gender}" '
        f'yob="{yob}" dob="{dob}" co="{careof}" house="{house}" street="{street}" '
        f'lm="Main Road" loc="{loc}" vtc="{vtc}" po="{vtc}" dist="{dist}" '
        f'subdist="{subdist}" state="{state}" pc="{pincode}"/>'
    )
    return xml

def main():
    parser = argparse.ArgumentParser(description="GoaOnAuto QR Code Generator Utility")
    parser.add_argument("--text", help="Text or URL to encode in standard QR code")
    parser.add_argument("--aadhaar", action="store_true", help="Generate synthetic Aadhaar XML QR code")
    parser.add_argument("--name", default="Anosh Chodankar", help="Name for Aadhaar QR")
    parser.add_argument("--dob", default="15/08/1999", help="DOB (DD/MM/YYYY) for Aadhaar QR")
    parser.add_argument("--gender", default="M", choices=["M", "F", "T"], help="Gender for Aadhaar QR")
    parser.add_argument("--house", default="H.No. 123", help="House No.")
    parser.add_argument("--taluka", default="Bardez", help="Taluka (Subdistrict)")
    parser.add_argument("--city", default="Mapusa", help="Village/City (VTC)")
    parser.add_argument("--pincode", default="403507", help="Pincode")
    parser.add_argument("--out", default="generated_qr.png", help="Output file path (default: generated_qr.png)")
    parser.add_argument("--size", type=int, default=512, help="Resolution size of QR code (default: 512px)")
    args = parser.parse_args()

    if args.aadhaar:
        payload = generate_aadhaar_xml(
            name=args.name,
            dob=args.dob,
            gender=args.gender,
            house=args.house,
            subdist=args.taluka,
            vtc=args.city,
            pincode=args.pincode
        )
        print(f"📦 Generating Synthetic Aadhaar QR for: {args.name} (DOB: {args.dob}, Taluka: {args.taluka})")
    elif args.text:
        payload = args.text
        print(f"📦 Generating standard QR code for text: {payload[:60]}...")
    else:
        # Default interactive or sample
        payload = "https://goaonline.gov.in"
        print(f"ℹ️  No text or --aadhaar provided. Generating sample QR code for: {payload}")

    try:
        saved_path = generate_qr_image(payload, out_path=args.out, size=args.size)
        print(f"✅ QR Code generated successfully at: {saved_path}")
    except Exception as e:
        print(f"❌ Error generating QR code: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
