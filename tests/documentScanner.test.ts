import { classifyDocumentText } from '../utils/documentClassifier';

// Mock OCR outputs for testing document classification logic

const MOCK_OCR_SAMPLES = {
  aadhaar: `
    GOVERNMENT OF INDIA
    Unique Identification Authority of India
    Rahul Sharma
    DOB: 15/08/1992
    Male
    5482 9102 3841
  `,
  pan: `
    INCOME TAX DEPARTMENT
    GOVT. OF INDIA
    PANKAJ KUMAR
    FATHER: RAMESH KUMAR
    DOB: 01/01/1990
    ABCDE1234F
  `,
  voter_id: `
    ELECTION COMMISSION OF INDIA
    ELECTOR IDENTITY CARD
    EPIC NO: WXZ1029481
    Name: Suresh Parab
    Father's Name: Anand Parab
  `,
  marriage_cert: `
    FORM NO. 16
    GOVERNMENT OF GOA
    OFFICE OF THE REGISTRAR OF MARRIAGES
    CERTIFICATE OF MARRIAGE
    This is to certify that John Doe and Jane Smith were married on 10/10/2020.
  `,
  birth_cert: `
    FORM NO. 5
    DEPARTMENT OF REGISTRATION OF BIRTHS AND DEATHS
    BIRTH CERTIFICATE
    Name of Child: Anosh Dsouza
    Date of Birth: 12/04/2001
    Place of Birth: Panaji Goa
  `,
  bonafide_primary: `
    GOVERNMENT PRIMARY SCHOOL TALEIGAO
    BONAFIDE CERTIFICATE
    This is to certify that Master Amit Rane is a bonafide student of Class III for academic year 2024-25.
  `,
  bonafide_college: `
    DON BOSCO COLLEGE OF ENGINEERING
    BONAFIDE STUDENT CERTIFICATE
    This is to certify that Miss Neha Sharma is a regular student enrolled in Mechanical Engineering.
  `,
  marksheet_ssc: `
    GOA BOARD OF SECONDARY AND HIGHER SECONDARY EDUCATION
    STATEMENT OF MARKS - CLASS X (SSC)
    Seat No: 109482
    Name: Rohit Sawant
    Result: PASS WITH DISTINCTION
  `,
  marksheet_university: `
    GOA UNIVERSITY
    OFFICE OF CONTROLLER OF EXAMINATIONS
    SEMESTER VI GRADE CARD & TRANSCRIPT
    PRN: 202109281
    CGPA: 8.92
    Grand Total: 850 / 1000
  `,
  electricity_bill: `
    GOVERNMENT OF GOA ELECTRICITY DEPARTMENT
    ELECTRICITY BILL
    Consumer No: 04928104
    CA No: 1029481
    Units Consumed: 245 KWH
    Total Amount Payable: Rs 1450.00
  `,
  house_tax: `
    VILLAGE PANCHAYAT OF TALEIGAO
    HOUSE TAX RECEIPT
    Assessment Year: 2024-2025
    House No: 142/A
    Paid by: Manuel Silva
  `,
  residence_cert: `
    OFFICE OF THE MAMLATDAR PANAJI
    RESIDENCE CERTIFICATE
    This is to certify that Shri Vikas Rane is a resident of House No 45, Miramar Goa for 15 years.
  `,
  caste_cert: `
    OFFICE OF THE SUB DIVISIONAL OFFICER
    CASTE CERTIFICATE
    This is to certify that Rohan Gawde belongs to Other Backward Class (OBC) community in Goa.
  `,
  ration_card: `
    DEPARTMENT OF FOOD & CIVIL SUPPLIES GOA
    RATION CARD (PHH)
    Card No: GA-10294-8192
    Head of Family: Maria Fernandez
    FPS Shop: 42
  `
};

console.log("=== Testing Document Classifier Logic ===");

for (const [expectedType, text] of Object.entries(MOCK_OCR_SAMPLES)) {
  const result = classifyDocumentText(text, 'sample.jpg');
  console.log(`Expected: ${expectedType} -> Detected: ${result.docType} (${result.docTypeName})`);
  console.log(`  Suggested Filename: ${result.suggestedFilename}`);
  console.log(`  Confidence: ${result.confidence * 100}%`);
  console.log(`  Extracted Name: ${result.extractedName || 'N/A'}`);
  console.log('---');
}
