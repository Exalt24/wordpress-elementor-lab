# genesis-lab

A WordPress build with a DEV site and a PROD site on one MariaDB, two child themes over one set of functionality, Advanced Custom Fields kept in code, a sync script that is the only road into PROD, and a page converted from a layered PSD mock-up.

![The page converted from the PSD mock-up on the PROD site at desktop width: a full width dark band with the headline and a button on the left and a picture block on the right](docs/mockup-wide.png)

*A screenshot of the real PROD page at 1280 pixels wide. The phone view stacks the picture under the text: [phone screenshot](docs/mockup-phone.png).*

The case study post type, its industry taxonomy, the ACF fields and the content filters live in one must-use plugin (`mu-plugins/lab-core.php`), so a theme change cannot lose them. Each child theme only places things with its parent's own hooks: `lab-classic` on Twenty Twenty-One uses `loop_start` and `wp_footer`, and `lab-child` on the Genesis Framework uses `genesis_before_loop` and `genesis_footer_creds_text`.

## What was measured

- `python scripts/check_lab.py` ran against both live sites with no failures: DEV and PROD both serve the three case study cards, the archive, the single page with its result first and the theme's footer credit. PROD carries no DEV address, keeps its own site name, runs the same theme as DEV, and a case study with script tags in its title and fields prints escaped.
- `python scripts/mutation_check.py` breaks a copy of the lab 13 ways (the REST flag, the taxonomy, ACF JSON saving, an unescaped field, the content filter, both ACF field names, the Template line of each theme, each theme's hook, case study logic put back into a theme) and the file checks caught all 13. Its first run found two checks that passed on a broken lab; both were tightened.
- A live version of the escaping break (the plugin printing a result without `esc_html`) failed two checks on the running site, then the file was restored.
- `node scripts/check_mockup.cjs` loads the converted page at 1280 and 390 pixels: the picture sits beside the text on a wide screen and under it on a phone, nothing spills past the screen width, and the band, button and picture colours are the ones read from the PSD.

## Run it

Docker, Python 3.13 with `psd-tools` and `pytoshop`, and Node are what it was run with.

```bash
bash scripts/setup.sh                 # DEV on 8091 and PROD on 8092, the lab-classic theme, ACF, three sample case studies
bash scripts/make_mockup_page.sh      # writes the PSD, converts it and creates the /mockup/ page on DEV
bash scripts/sync_dev_to_prod.sh      # PROD is backed up first, then takes DEV's content with every address rewritten
python scripts/check_lab.py           # the file checks and the live checks
```

`THEME=lab-child bash scripts/setup.sh` builds the same lab on the Genesis Framework. The framework is a free zip that StudioPress emails on request (https://www.studiopress.com/get-genesis/); save it as `vendor/genesis.zip` first.

## Limits

- The Genesis theme was written and its file checks pass, but it has not been run against the framework: the zip request returned no email.
- The PSD is written by `scripts/make_mockup_psd.py` with pytoshop, which writes pixel layers and no type layers, so each layer name carries its role and text. A designer's file needs the same layer names.
- The converter builds a two column band from layer positions and colours. It is not a pixel copy of the canvas.
- The sync moves the database only. This lab has no uploads, so none are copied.
- Local Docker only: no real hosting, no domain and no traffic.
