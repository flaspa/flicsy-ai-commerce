/* Flicsy Phase 1 mock data.
 * Products, prices, sale prices and stock come from Everlane's public catalog (snapshot 2026-10-03).
 * Press and social evidence are illustrative placeholders until Tavily and Bright Data are connected. */

const IMG = (handle, n = 1) => `/img/products/${handle}-${n}.jpg`;
const EVERLANE = (handle) => `https://www.everlane.com/products/${handle}`;

export const AGENTS = {
  miranda: { name: "Miranda", role: "Lead Stylist", img: "/characters/miranda.png", handle: "@miranda",
    question: "What does this client actually need?",
    line: "Talks to you, writes the brief, delegates, and makes the final selection." },
  andy: { name: "Andy", role: "Fashion Editor", img: "/characters/andy.png", handle: "@andy", tool: "Tavily",
    question: "What does the fashion establishment suggest?",
    line: "Reads the fashion press for silhouettes, colour and editorial direction." },
  emily: { name: "Emily", role: "Social & Culture Editor", img: "/characters/emily.png", handle: "@emily", tool: "Bright Data",
    question: "What are people actually wearing and talking about?",
    line: "Reads social culture through the Mira Picks clipping book." },
  serena: { name: "Serena", role: "Personal Shopper", img: "/characters/serena.png", handle: "@serena", tool: "Moss",
    question: "What can the client actually buy?",
    line: "Searches retailer catalogs and assembles complete, purchasable looks." },
  nigel: { name: "Nigel", role: "Fashion Director", img: "/characters/nigel.png", handle: "@nigel",
    question: "Does this actually work as a look for this client?",
    line: "Critiques fit, occasion, budget and evidence. Can reject a piece." },
};

/* The visible workflow: Miranda appears twice, as in Mira Picks. */
export const STAGES = [
  { id: "brief", agent: "miranda", title: "Miranda — Brief", sub: "Lead Stylist" },
  { id: "andy", agent: "andy", title: "Andy", sub: "Fashion Editor · Tavily" },
  { id: "emily", agent: "emily", title: "Emily", sub: "Social & Culture · Bright Data" },
  { id: "serena", agent: "serena", title: "Serena", sub: "Personal Shopper · Moss" },
  { id: "nigel", agent: "nigel", title: "Nigel", sub: "Fashion Director · Critic" },
  { id: "final", agent: "miranda", title: "Miranda — Final edit", sub: "Lead Stylist · decides" },
];

export const PRODUCTS = {
  halter: { retailer: "Everlane", name: "Textured Halter Midi Dress", color: "Open Air Blue", price: 101, was: 168,
    stock: "In stock · 9 of 10 sizes", img: IMG("womens-textured-halter-midi-dress-open-air-blue"),
    img2: IMG("womens-textured-halter-midi-dress-open-air-blue", 2), url: EVERLANE("womens-textured-halter-midi-dress-open-air-blue") },
  scarf: { retailer: "Everlane", name: "Wool Cashmere Tie-Front Scarf", color: "Celestial Blue", price: 78,
    stock: "In stock · one size", img: IMG("u-accs-wlc-scrf-hood-clst"), url: EVERLANE("u-accs-wlc-scrf-hood-clst") },
  mule: { retailer: "Everlane", name: "Glove Mule Slipper", color: "Black Leather", price: 168,
    stock: "In stock · all sizes", img: IMG("womens-glove-mule-slipper-black-leather"), url: EVERLANE("womens-glove-mule-slipper-black-leather") },
  blazer: { retailer: "Everlane", name: "The Dream Blazer", color: "Navy", price: 50, was: 168,
    stock: "Low stock · XXS–XS", low: true, img: IMG("womens-dream-blazer-navy"), url: EVERLANE("womens-dream-blazer-navy") },
  trouser: { retailer: "Everlane", name: "Tropical Wool Trouser (men's)", color: "Dark Navy", price: 198,
    stock: "In stock · 16 of 18 sizes", img: IMG("mens-tropical-wool-trouser-dark-navy"), url: EVERLANE("mens-tropical-wool-trouser-dark-navy") },
  boot: { retailer: "Everlane", name: "Collegium x Everlane Summit Boot", color: "Navy Suede", price: 379,
    stock: "In stock", img: IMG("u-ftwr-cgm-sum-boot-nvy"), url: EVERLANE("u-ftwr-cgm-sum-boot-nvy") },
  slingback: { retailer: "Everlane", name: "The Ballet Slingback Heel", color: "Black", price: 57, was: 228,
    stock: "Last size · 6", low: true, img: IMG("womens-ballet-slingback-heel-black"), url: EVERLANE("womens-ballet-slingback-heel-black") },
  slip: { retailer: "Everlane", name: "Slip Dress in Silk Charmeuse", color: "Black", price: 50, was: 248,
    stock: "In stock · all sizes", img: IMG("womens-strapless-dress-in-silk-charmeuse-black"),
    img2: IMG("womens-strapless-dress-in-silk-charmeuse-black", 2), url: EVERLANE("womens-strapless-dress-in-silk-charmeuse-black") },
  puffer: { retailer: "Everlane", name: "EverPuff Cloud Short Puffer", color: "Cashmere Blue", price: 228,
    stock: "In stock · XXS–XL", img: IMG("f-otwr-mlc-puff-sht-cblu"), url: EVERLANE("f-otwr-mlc-puff-sht-cblu") },
  pump: { retailer: "Everlane", name: "The Banana Pump", color: "Black Suede", price: 50, was: 198,
    stock: "Last size · 5", low: true, img: IMG("womens-banana-pump-black-suede"), url: EVERLANE("womens-banana-pump-black-suede") },
};

export const LOOKS = [
  { id: "I", title: "Open Air Blue", hero: PRODUCTS.halter.img, items: ["halter", "scarf", "mule"],
    rationale: "Your blue, worn like you mean it. The halter keeps it from feeling conservative, the cashmere scarf is the only nod to the mountains, and the glove mule says you chose comfort on purpose.",
    nigel: "Works. Elegant without a single conventional choice." },
  { id: "II", title: "Borrowed Tailoring", hero: PRODUCTS.blazer.img, items: ["blazer", "trouser", "slingback"],
    rationale: "A navy suit borrowed from the men's floor, softened by a ballet slingback. It reads black tie from across the room and nothing like what anyone else will wear.",
    nigel: "Works after revision. I rejected the Summit Boot — too literal.", revised: { from: "boot", to: "slingback" } },
  { id: "III", title: "Après-Ski After Dark", hero: PRODUCTS.puffer.img, items: ["slip", "puffer", "pump"], alt: true,
    rationale: "The alternative direction. Silk charmeuse under a cloud-blue puffer: the skier's joke, told well. Take it off at the door and you are in a perfect black slip.",
    nigel: "Bold. It lands if she wants the joke. Pump is down to its last size 5." },
];

export const PRESS = {
  note: "Illustrative evidence · Tavily search connects in Phase 2",
  query: "unconventional evening dressing 2026 · tailoring · blue",
  sources: [
    { name: "Vogue", status: "read", headline: "Evening tailoring loosens its tie", why: "Suiting as eveningwear" },
    { name: "Harper's Bazaar", status: "read", headline: "The new blues: icy, saturated, unexpected after dark", why: "Colour direction" },
    { name: "The Cut", status: "read", headline: "Flats at formal events are no longer a compromise", why: "Footwear" },
    { name: "Business of Fashion", status: "read", headline: "Quiet luxury gives way to personality", why: "Market mood" },
    { name: "WWD", status: "paywalled", headline: "Subscriber-only — skipped, not bypassed", why: "" },
  ],
  signals: [
    { signal: "Sculptural and borrowed tailoring after dark", strength: "high" },
    { signal: "Saturated and icy blues replace black as the evening neutral", strength: "medium" },
    { signal: "Low heels and formal flats are accepted at black-tie events", strength: "medium" },
  ],
};

export const CLIPS = {
  note: "Illustrative clips · Bright Data clipping book connects in Phase 2",
  stats: "24 clips matched · 762 in the Mira Picks clipping book",
  aesthetics: ["Slip dress + outerwear", "Formal flats", "Monochrome blue"],
  clips: [
    { text: "gala fit but make it comfortable — mules all night", tags: ["formalflats", "galaoutfit"], plays: "1.2M", tone: "#2a3550" },
    { text: "wearing my puffer over the slip dress and NOT taking notes", tags: ["slipdress", "winterstyle"], plays: "860K", tone: "#8fb3d9" },
    { text: "one colour head to toe: cobalt edition", tags: ["monochrome", "blueoutfit"], plays: "540K", tone: "#2f5cc4" },
    { text: "borrowed my dad's suit for black tie and it worked", tags: ["suiting", "eveningtailoring"], plays: "2.4M", tone: "#1b1f2a" },
  ],
};

export const NIGEL_NOTES = {
  checks: [
    ["Occasion", "Black-tie appropriate", "ok"],
    ["Budget", "All looks within budget after revision", "ok"],
    ["Palette", "Blue carried in every look", "ok"],
    ["Footwear", "No stilettos", "ok"],
    ["Evidence", "Press and social agree on tailoring and flats", "ok"],
    ["Availability", "Two pieces are down to their last size", "warn"],
  ],
  rejection: { look: "II", item: "boot", reason: "A hiking boot at a gala is a costume, not a reference. And at $379 it costs more than the rest of the look combined." },
};

/* One scripted run. `at` is milliseconds from the start. Drives the Fashion Desk cards
 * and the Behind the Curtain room from the same timeline. */
export function buildScript(brief) {
  const b = brief;
  return [
    { at: 0, stage: "brief", state: "working", line: "Writing the brief…",
      room: { kind: "system", text: `Room opened · ${b.occasion} · ${b.city}` } },
    { at: 900, room: { from: "miranda", text: `Brief: ${b.occasion}, ${b.city}. ${b.dressCode}. Budget ${b.budget}. ${b.silhouette}. Loves blue and skiing; wants elegant, not conventional. Avoid: ${b.dislikes}.` } },
    { at: 1800, stage: "brief", state: "done", line: "Brief sent to the desk" },
    { at: 1900, room: { from: "miranda", text: "@andy What is the establishment saying about evening dressing that isn't conservative?", mentions: ["andy"] } },
    { at: 2300, room: { from: "miranda", text: "@emily What are people actually wearing to formal events right now?", mentions: ["emily"] } },

    { at: 2500, stage: "andy", state: "working", line: "Searching the fashion press…" },
    { at: 2700, stage: "emily", state: "working", line: "Opening the clipping book…" },
    { at: 3200, room: { kind: "tool", from: "andy", tool: "tavily.search", args: `"${PRESS.query}"`, result: "8 results · 5 publications" } },
    { at: 3600, room: { kind: "tool", from: "emily", tool: "brightdata.clipbook.query", args: `["formal flats", "evening tailoring", "blue eveningwear"]`, result: "24 of 762 clips matched" } },
    { at: 4100, stage: "andy", line: "Reading Vogue, Harper's Bazaar, The Cut…" },
    { at: 4600, stage: "emily", line: "Reading 24 clips…" },
    { at: 5600, stage: "andy", line: "Interpreting silhouettes and colour…" },
    { at: 6400, stage: "andy", state: "done", line: "3 press signals · 4 sources read", reveal: "press",
      room: { from: "andy", text: "@serena Editorial direction: borrowed tailoring after dark, saturated and icy blues, low or flat formal shoes. WWD paywalled — skipped.", mentions: ["serena"], handoff: true } },
    { at: 7200, stage: "emily", state: "done", line: "3 aesthetics · 24 clips", reveal: "clips",
      room: { from: "emily", text: "@serena Socially: mules and flats over stilettos, slip dresses layered under outerwear, one colour head to toe in blue.", mentions: ["serena"], handoff: true } },

    { at: 7500, stage: "serena", state: "working", line: "Searching the Everlane catalog…" },
    { at: 8000, room: { kind: "tool", from: "serena", tool: "moss.search", args: `"elegant unconventional gala, blue, no stilettos" {retailer: everlane, in_stock: true}`, result: "1,500 indexed · 42 candidates · 9 ms" } },
    { at: 8800, stage: "serena", line: "Assembling three complete looks…" },
    { at: 9800, stage: "serena", line: "Checking sizes and availability…" },
    { at: 10700, stage: "serena", state: "done", line: "3 looks in the bag", reveal: "bag", bag: "draft",
      room: { from: "serena", text: "@nigel Three complete looks: I · Open Air Blue $347 · II · Borrowed Tailoring $627 · III · Après-Ski After Dark $328.", mentions: ["nigel"], handoff: true } },

    { at: 11000, stage: "nigel", state: "working", line: "Reviewing three looks…" },
    { at: 12000, stage: "nigel", line: "Checking occasion, budget and footwear…" },
    { at: 13200, stage: "nigel", state: "blocked", line: "Rejected one piece in Look II",
      room: { kind: "reject", from: "nigel", text: `@serena Look II — reject the Summit Boot. ${NIGEL_NOTES.rejection.reason} Replace with a refined evening shoe.`, mentions: ["serena"] } },
    { at: 13600, stage: "serena", state: "working", line: "Replacing Look II shoes…" },
    { at: 14200, room: { kind: "tool", from: "serena", tool: "moss.search", args: `"black evening shoe, low heel, refined" {max_price: 120}`, result: "11 candidates · 7 ms" } },
    { at: 15300, stage: "serena", state: "done", line: "Look II revised", bag: "revised",
      room: { from: "serena", text: "@nigel Revised Look II: The Ballet Slingback Heel, black, $57. New total $305.", mentions: ["nigel"], handoff: true } },
    { at: 15700, stage: "nigel", state: "working", line: "Re-checking Look II…" },
    { at: 16900, stage: "nigel", state: "done", line: "Approved with one caveat", reveal: "notes",
      room: { from: "nigel", text: "@miranda I and II are coherent with the brief. III is the bold one — it works if she wants the joke. Flag the last-size pump.", mentions: ["miranda"], handoff: true } },

    { at: 17200, stage: "final", state: "working", line: "Making the final selection…" },
    { at: 18800, stage: "final", state: "done", line: "Three looks selected", reveal: "verdict",
      room: { kind: "approve", from: "miranda", text: "Approved. Present I and II as the edit, III as the alternative direction." } },
    { at: 19300, room: { kind: "system", text: "Handoff → customer · Miranda's Edit is ready" }, end: true },
  ];
}
