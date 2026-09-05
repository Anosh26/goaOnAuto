import { synthesizeDossier, ExtractedDocument } from '../src/classifier';
import { AadhaarQrResult } from '../src/scanner/gpuDaemonClient';

const docs: ExtractedDocument[] = [
  {
    docType: 'residence_cert',
    docTypeName: 'Residence Certificate',
    rawText: 'This is to certify that John Doe is residing at Mapusa for the last 15 years continuously.',
    filePath: 'residence_cert.jpg'
  },
  {
    docType: 'bonafide_cert',
    docTypeName: 'Bonafide Certificate',
    rawText: 'Bonafide student from 2012 to 2024.',
    filePath: 'bonafide.jpg'
  }
];

const qrResult: AadhaarQrResult = {
  success: true,
  name: "John Doe",
  dob: "12-05-1990",
  gender: "M",
  loc: "Mapusa",
  dist: "North Goa",
  state: "Goa"
};

const dossier = synthesizeDossier(docs, qrResult);
console.log(JSON.stringify(dossier, null, 2));
