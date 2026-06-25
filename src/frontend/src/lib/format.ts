export const SEV_COLOR = { fatal: "#ef4444", serious: "#f59e0b", light: "#3b82f6", all: "#22d3ee" } as const;
export const STATES: { code: string; name: string }[] = [
  { code: "", name: "All Germany" },
  { code: "BW", name: "Baden-Württemberg" }, { code: "BY", name: "Bayern" },
  { code: "BE", name: "Berlin" }, { code: "BB", name: "Brandenburg" },
  { code: "HB", name: "Bremen" }, { code: "HH", name: "Hamburg" },
  { code: "HE", name: "Hessen" }, { code: "MV", name: "Mecklenburg-Vorpommern" },
  { code: "NI", name: "Niedersachsen" }, { code: "NW", name: "Nordrhein-Westfalen" },
  { code: "RP", name: "Rheinland-Pfalz" }, { code: "SL", name: "Saarland" },
  { code: "SN", name: "Sachsen" }, { code: "ST", name: "Sachsen-Anhalt" },
  { code: "SH", name: "Schleswig-Holstein" }, { code: "TH", name: "Thüringen" },
];
const nf = new Intl.NumberFormat("en-US");
export const fmt = (n: number | null | undefined) => (n == null ? "—" : nf.format(n));
