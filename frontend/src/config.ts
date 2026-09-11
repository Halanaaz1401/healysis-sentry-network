export const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host !== "localhost" && host !== "127.0.0.1") {
      return "https://healysis-sentry-network.onrender.com";
    }
  }
  if (process.env.NODE_ENV === "production") {
    return "https://healysis-sentry-network.onrender.com";
  }
  return "http://localhost:8000";
};

export const API_BASE_URL = getApiBaseUrl();

export interface UserIdentity {
  firebase_uid: string;
  email: string;
  full_name: string;
  role: "ADMIN" | "CDMO" | "FACILITY_OFFICER";
  facility_id: number | null;
  facility_name: string;
  token: string;
}

export const MOCK_USERS: UserIdentity[] = [
  {
    firebase_uid: "UID-ADMIN-99",
    email: "admin@healysis.gov.in",
    full_name: "System Admin",
    role: "ADMIN",
    facility_id: null,
    facility_name: "Global System Wide Scope",
    token: "Bearer TEST-TOKEN-UID-ADMIN-99"
  },
  {
    firebase_uid: "UID-CDMO-88",
    email: "cdmo.director@healysis.gov.in",
    full_name: "Dr. S. Mohanty (CDMO)",
    role: "CDMO",
    facility_id: null,
    facility_name: "State Health Director Hub (Odisha & WB)",
    token: "Bearer TEST-TOKEN-UID-CDMO-88"
  },
  {
    firebase_uid: "UID-OFFICER-JATNI",
    email: "officer.jatni@healysis.gov.in",
    full_name: "Dr. A. Nayak",
    role: "FACILITY_OFFICER",
    facility_id: 1,
    facility_name: "Jatni CHC (Khordha)",
    token: "Bearer TEST-TOKEN-UID-OFFICER-JATNI"
  },
  {
    firebase_uid: "UID-OFFICER-MSDAS",
    email: "pharmacist.cuttack@healysis.gov.in",
    full_name: "S. Patra (Pharmacist)",
    role: "FACILITY_OFFICER",
    facility_id: 2,
    facility_name: "UPHC MS Das (Kafla Bazar)",
    token: "Bearer TEST-TOKEN-UID-OFFICER-MSDAS"
  },
  {
    firebase_uid: "UID-OFFICER-PIPILI",
    email: "inventory.pipili@healysis.gov.in",
    full_name: "R. Mohanty",
    role: "FACILITY_OFFICER",
    facility_id: 3,
    facility_name: "Pipili PHC (Puri)",
    token: "Bearer TEST-TOKEN-UID-OFFICER-PIPILI"
  },
  {
    firebase_uid: "UID-OFFICER-BEHALA",
    email: "nurse.behala@healysis.gov.in",
    full_name: "T. Banerjee",
    role: "FACILITY_OFFICER",
    facility_id: 4,
    facility_name: "Behala Urban PHC (Kolkata)",
    token: "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"
  },
  {
    firebase_uid: "UID-OFFICER-DIAMOND",
    email: "officer.diamond@healysis.gov.in",
    full_name: "K. Biswas",
    role: "FACILITY_OFFICER",
    facility_id: 5,
    facility_name: "Diamond Harbour PHC",
    token: "Bearer TEST-TOKEN-UID-OFFICER-DIAMOND"
  }
];
