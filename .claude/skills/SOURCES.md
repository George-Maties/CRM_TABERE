# Skill-uri externe

Skill-uri de design preluate din comunitate pe 2026-10-23, alese după popularitatea pe GitHub. Fiecare a fost citit înainte de instalare.

| Skill | Sursă | Versiune | Licență | Ce s-a schimbat local |
|---|---|---|---|---|
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills) (★183k) | `dbd4588` (2026-10-09) | vezi `LICENSE.txt` | nimic |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (★139k) | `d14efff` (2026-10-23) | MIT | căile scriptului (`${CLAUDE_PLUGIN_ROOT}/...` → `.claude/skills/ui-ux-pro-max/...`); eliminate testele, `validate_data.py` și 4 fișiere de date nefolosite la rulare |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (★85k) | `5cb95ee` (2026-10-23) | Apache-2.0 | fără `scripts/` (launcher-ul descarcă și rulează un binar); notă de instalare la începutul `SKILL.md` |
| `web-design-guidelines` | [vercel-labs/web-interface-guidelines](https://github.com/vercel-labs/web-interface-guidelines) (regulile, MIT) + [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) (★33k) | `434b7f9` (2026-10-05) | MIT | regulile salvate local în `guidelines.md`, în loc să fie descărcate la fiecare rulare; `SKILL.md` rescris pentru Django + Bootstrap |

Neinstalat: [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (★101k). Cere Node 22 și Chrome și e gândit pentru site-uri de prezentare, nu pentru aplicații.

Skill-urile proprii ale proiectului (`ui-conventions`, `new-section`, `new-page`, `new-component`, `ui-review`) au prioritate față de cele de mai sus.

## Actualizare

Nu se actualizează automat. Pentru o versiune nouă: descărcați repository-ul, citiți diferențele (mai ales scripturile), refaceți modificările locale din tabel și actualizați versiunea aici.
