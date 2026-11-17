# Vastgepind: CIm VTH FLo (Conceptueel Informatiemodel VTH Fysieke Leefomgeving)

`0.9.1/model.json` — machine-leesbaar extract van
`docs/EvT Conceptueel Informatiemodel Fysieke Leefomgeving VTH 0.9.1 07-2025 AVG.pdf`
(Programma Digitaal VTH-stelsel Milieu, project *Eenheid van Taal*; MIM-gebaseerd;
conceptversie 14-07-2025 — de AVG-geanonimiseerde publicatievariant, redacties
uitsluitend in documenthistorie en bronnenlijst). Metadata: `0.9.1/pin.json`.

Bevat: 33 objecttypen (definities, toelichtingen, attribuutsoorten en
relatiesoorten uit h5-detailblokken), 10 generalisaties (uit de h4-overzichtstabellen),
gegevensgroeptype Adres, relatieklasse *Mutatie specifiek voorschrift* en 4
referentielijsten (Controletype, Controle-onderwerp, Handhavingsinstrument,
Type VTH-object) met hun referentie-elementen. Bekende beperkingen staan in
`model.json → model.opmerkingen` (kern-objecttypen per view staan alleen in
figuren; KLACHT/SIGNAAL hebben geen h5-detailhoofdstuk; waardenlijsten worden
buiten het model beheerd).

Regeneratie (deterministisch, byte-stabiel):

    python3 nldt/scripts/extract_cim_vth_flo.py            # vereist pdftotext

Vastgepinde checks: `nldt/tests/test_cim_vth_flo.py`. Bij de 1.0-vaststelling:
nieuwe versiemap genereren met hetzelfde script en de nieuwe PDF, pin bijwerken,
tests verlengen — patroon conform `nldt/simulation/regelrecht/schema/`.
