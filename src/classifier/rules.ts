/**
 * Document Classification Rules Dictionary.
 * Single Responsibility: Defines keyword mappings, regex patterns, and priorities for all supported documents.
 */
import { DocumentTypeRule } from './types';

export const DOCUMENT_RULES: DocumentTypeRule[] = [
  {
    id: 'aadhaar',
    name: 'Aadhaar Card',
    keywords: ['unique identification authority', 'government of india', 'aadhaar', 'uidai', 'year of birth'],
    patterns: [/\b\d{4}\s?\d{4}\s?\d{4}\b/],
    priority: 10
  },
  {
    id: 'pan',
    name: 'PAN Card',
    keywords: ['income tax department', 'govt of india', 'permanent account number', 'pan card'],
    patterns: [/\b[A-Z]{5}[0-9]{4}[A-Z]\b/],
    priority: 10
  },
  {
    id: 'driving_license',
    name: 'Driving License',
    keywords: ['driving licence', 'transport department', 'licence no', 'dl no', 'form 7'],
    patterns: [/\b[A-Z]{2}[- ]?\d{2}[- ]?\d{11}\b/i],
    priority: 9
  },
  {
    id: 'passport',
    name: 'Passport',
    keywords: ['republic of india', 'passport no', 'type p', 'indian passport', 'given name', 'place of issue'],
    patterns: [/\b[A-Z][0-9]{7}\b/],
    priority: 9
  },
  {
    id: 'voter_id',
    name: 'Voter ID Card',
    keywords: [
      'election commission of india', 
      'election commission', 
      'elector identity card', 
      'identity card',
      'voter id', 
      'voter', 
      'epic', 
      'epic no', 
      'epic number', 
      'electoral registration officer', 
      'assembly constituency'
    ],
    patterns: [/\b[A-Z]{3}[0-9]{7}\b/i],
    priority: 10
  },
  {
    id: 'marriage_cert',
    name: 'Marriage Certificate',
    keywords: ['marriage certificate', 'certificate of marriage', 'civil registration', 'civil registrar', 'office of civil registrar', 'solemnization of marriage', 'registrar of marriages', 'form no 16', 'groom', 'bride'],
    priority: 8
  },
  {
    id: 'birth_cert',
    name: 'Birth Certificate',
    keywords: ['birth certificate', 'certificate of birth', 'registration of births and deaths', 'date of birth', 'form no 5', 'name of child', 'place of birth'],
    priority: 8
  },
  {
    id: 'bonafide_cert',
    name: 'Bonafide Certificate',
    keywords: [
      'bonafide certificate', 
      'bonafide student', 
      'this is to certify that', 
      'regular student', 
      'enrolled as a student',
      'bonafide', 
      'academic year', 
      'roll no', 
      'gr no',
      'school', 
      'primary school',
      'high school', 
      'higher secondary school',
      'hssc', 
      'ssc',
      'junior college',
      'college', 
      'university', 
      'polytechnic',
      'institute of technology',
      'headmaster',
      'headmistress',
      'principal',
      'dean',
      'registrar'
    ],
    priority: 8
  },
  {
    id: 'electricity_bill',
    name: 'Electricity Bill',
    keywords: ['electricity department', 'electricity bill', 'units consumed', 'kwh', 'consumer no', 'ca no', 'bill amount', 'power distribution'],
    priority: 8
  },
  {
    id: 'house_tax',
    name: 'House Tax / Property Tax',
    keywords: ['house tax', 'property tax', 'village panchayat', 'municipal council', 'tax receipt', 'assessment year', 'house no'],
    priority: 8
  },
  {
    id: 'residence_cert',
    name: 'Residence Certificate',
    keywords: ['residence certificate', 'certificate of residence', 'resident of', 'mamlatdar', 'sub divisional officer', 'residing at'],
    priority: 8
  },
  {
    id: 'caste_cert',
    name: 'Caste Certificate',
    keywords: ['caste certificate', 'community certificate', 'scheduled caste', 'scheduled tribe', 'other backward class', 'obc', 'belongs to caste'],
    priority: 8
  },
  {
    id: 'samaj_cert',
    name: 'Samaj Certificate',
    keywords: ['samaj certificate', 'samaj', 'sanstha', 'community association', 'samajik', 'trust'],
    priority: 7
  },
  {
    id: 'ration_card',
    name: 'Ration Card',
    keywords: ['ration card', 'civil supplies', 'food and civil supplies', 'head of family', 'fps', 'card no', 'aph', 'phh', 'nphh'],
    priority: 8
  },
  {
    id: 'pcc',
    name: 'Police Clearance Certificate (PCC)',
    keywords: ['police clearance certificate', 'police clearance', 'pcc', 'police station', 'passport office', 'no criminal record'],
    priority: 9
  },
  {
    id: 'obc_cert',
    name: 'OBC Certificate',
    keywords: ['other backward class', 'obc certificate', 'obc', 'creamy layer', 'non creamy layer'],
    priority: 9
  },
  {
    id: 'marksheet',
    name: 'Marksheet / Academic Certificate',
    keywords: [
      'marks statement', 
      'statement of marks', 
      'marksheet', 
      'mark sheet', 
      'grade card', 
      'transcript', 
      'passing certificate', 
      'board of secondary education', 
      'board of higher secondary education', 
      'goa board', 
      'cbse', 
      'icse', 
      'university', 
      'controller of examinations', 
      'semester', 
      'trimester', 
      'seat no', 
      'roll no', 
      'prn', 
      'register no', 
      'cgpa', 
      'sgpa', 
      'total marks', 
      'marks obtained', 
      'grand total', 
      'class awarded', 
      'distinction'
    ],
    priority: 8
  },
  {
    id: 'passport_photo',
    name: 'Passport Size Photo',
    keywords: [
      'passport photo',
      'passport size photo',
      'applicant photo',
      'recent photograph',
      'photo of applicant',
      'affix photograph',
      'photograph'
    ],
    priority: 10
  },
  {
    id: 'signature',
    name: 'Signature',
    keywords: [
      'specimen signature',
      'signature of applicant',
      'signature',
      'sign of applicant',
      'applicant signature',
      'sign here'
    ],
    priority: 9
  }
];
