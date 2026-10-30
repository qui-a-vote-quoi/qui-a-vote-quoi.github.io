// Contrôle automatique d'accessibilité du site (règles dans ACCESSIBILITE.md).
// Ouvre chaque vue en clair et en sombre, sur ordinateur et sur mobile, et vérifie :
//  - les règles WCAG 2.1 A et AA testables automatiquement (axe-core), plus la taille des zones cliquables ;
//  - les règles propres au site : un seul h1, titre d'onglet, focus sur le titre au changement de vue,
//    pas de défilement horizontal à 320 px, liens vers un nouvel onglet signalés.
// Usage : cd outils/accessibilite && npm install && npx playwright install chromium (une fois), puis npm run verifier
// Sortie : la liste des problèmes, et un code de sortie 1 s'il y en a.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const SITE = fileURLToPath(new URL("../../site/", import.meta.url));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".svg": "image/svg+xml", ".woff2": "font/woff2", ".css": "text/css" };

// Petit serveur local du dossier site/
const serveur = createServer(async (req, res) => {
  const chemin = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname)).replace(/^\/+/, "") || "index.html";
  try { res.writeHead(200, { "Content-Type": TYPES[extname(chemin)] || "application/octet-stream" }); res.end(await readFile(join(SITE, chemin))); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise(r => serveur.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${serveur.address().port}/`;

const navigateur = await chromium.launch();
const problemes = [];
const signaler = (ou, regle, detail) => problemes.push({ ou, regle, detail });

// Les vues à contrôler : les adresses fixes, puis des exemples tirés des données (texte voté plusieurs fois, niche…)
async function vues() {
  const page = await navigateur.newPage();
  await page.goto(BASE);
  const ex = await page.evaluate(() => {
    const multi = Object.values(VOTES_DOSSIER).find(vs => vs.length > 2)?.at(-1);
    const avecDebat = TEXTES.find(t => t.debat), niche = NICHES[0], sujet = TEXTES[0].theme;
    return { multi: multi?.id, debat: avecDebat?.id, niche: niche?.date, sujet };
  });
  await page.close();
  return ["", "#groupes", "#sujets", `#sujet/${encodeURIComponent(ex.sujet)}`, `#texte/${ex.multi}`, `#texte/${ex.debat}`,
    "#groupe/SOC", "#groupe/NI", `#niche/${ex.niche}`, "#bilan", "#methode", "#apropos"];
}

const CONTEXTES = [
  { nom: "ordinateur clair", viewport: { width: 1280, height: 900 }, colorScheme: "light" },
  { nom: "ordinateur sombre", viewport: { width: 1280, height: 900 }, colorScheme: "dark" },
  { nom: "mobile clair", viewport: { width: 375, height: 812 }, colorScheme: "light", isMobile: true, hasTouch: true },
];

for (const ctx of CONTEXTES) {
  const contexte = await navigateur.newContext({ viewport: ctx.viewport, colorScheme: ctx.colorScheme, isMobile: ctx.isMobile, hasTouch: ctx.hasTouch, reducedMotion: "reduce" });
  const page = await contexte.newPage();
  const erreurs = [];
  page.on("pageerror", e => erreurs.push(e.message));
  for (const vue of await vues()) {
    const ou = `${vue || "accueil"} (${ctx.nom})`;
    await page.goto(BASE + vue);
    await page.waitForTimeout(150);
    // 1. axe-core : WCAG 2.1 A/AA, et la taille des zones cliquables (24 px, WCAG 2.2)
    const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).include("body").analyze();
    const cible = await new AxeBuilder({ page }).withRules(["target-size"]).analyze();
    for (const v of [...r.violations, ...cible.violations])
      signaler(ou, `${v.id} (${v.impact})`, `${v.help} — ${v.nodes.length} élément(s), ex. ${v.nodes[0].target.join(" ")}`);
    // 2. Règles propres au site
    const s = await page.evaluate(() => ({
      h1: document.querySelectorAll("main h1").length,
      titre: document.title,
      onglet: [...document.querySelectorAll('a[target="_blank"]')].filter(a => !/nouvel onglet/.test(a.textContent)).map(a => a.textContent.trim().slice(0, 40)),
    }));
    if (s.h1 !== 1) signaler(ou, "un seul h1", `${s.h1} titre(s) h1 dans la vue`);
    if (!/ – Qui a voté quoi$/.test(s.titre) && vue) signaler(ou, "titre d'onglet", `« ${s.titre} »`);
    if (s.onglet.length) signaler(ou, "nouvel onglet signalé", `liens sans « nouvel onglet » : ${s.onglet.join(", ")}`);
  }
  // Focus sur le titre au changement de vue (navigation interne)
  await page.goto(BASE);
  await page.evaluate(() => { location.hash = "#groupes"; });
  await page.waitForTimeout(150);
  if (!(await page.evaluate(() => document.activeElement?.tagName === "H1"))) signaler(`navigation (${ctx.nom})`, "focus sur le titre", "après un changement de vue, le focus n'est pas sur le h1");
  for (const e of erreurs) signaler(ctx.nom, "erreur JavaScript", e);
  await contexte.close();
}

// Pas de défilement horizontal à 320 px (zoom 400 %)
const etroit = await navigateur.newPage({ viewport: { width: 320, height: 700 } });
for (const vue of await vues()) {
  await etroit.goto(BASE + vue);
  await etroit.waitForTimeout(100);
  const debord = await etroit.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (debord > 0) signaler(`${vue || "accueil"} (320 px)`, "défilement horizontal", `la page dépasse de ${debord} px`);
}

await navigateur.close();
serveur.close();

if (!problemes.length) { console.log("Accessibilité : aucun problème détecté automatiquement."); }
else {
  console.log(`Accessibilité : ${problemes.length} problème(s)\n`);
  for (const p of problemes) console.log(`- ${p.ou} · ${p.regle}\n  ${p.detail}`);
}
console.log("\nRappel : ce contrôle ne remplace pas un test au clavier et au lecteur d'écran (voir ACCESSIBILITE.md).");
process.exitCode = problemes.length ? 1 : 0;
