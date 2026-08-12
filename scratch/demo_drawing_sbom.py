from wikid_steward.core.handlers import DrawingHandler

drawing_md_input = """# CAD Drawing: DWG-2026-X88

## Drawing Notes & Assembly Specs
- ITEM 01: MicroController MCU-ARM - Spec 32-bit Cortex M4 - Qty 1
- ITEM 02: Power Module PM-12V - Spec 12V 5A DC-DC - Qty 2
- ITEM 03: Sensor Array SEN-04 - Spec SPI Bus Temp Sensor - Qty 4

## Section A-A View
(Drawing schematic content...)
"""

handler = DrawingHandler()
output_md = handler.post_process_markdown(drawing_md_input, "drawing")

print("=== Demonstration: Drawing Profile SBOM Parse Output ===")
print(output_md[:1000])
