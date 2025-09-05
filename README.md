# KLayout Plugin: Layer Shortcuts

<!--
[![Watch the demo](doc/screenshot-demo-video.gif)](https://youtube.com/watch/v=TODO)
-->

* Boost your layout productivity with shortcuts 
   * to quickly change layer visibility
   
This add-on can be installed through [KLayout](https://klayout.de) package manager, [see installation instructions here](#installation-instructions)

## Usage

### Tool activation and deactivation

- Activate or deactivate the *Layer Shortcuts* plugin by selecting *Tools*→*Layer Shortcut Plugin* in the main menu

### Shortcuts

Shortcuts can be defined as action steps in the JSON configuration file.

This following table describes the shortcuts of our default IHP SG13G2 configuration.

| Shortcut | Description (What happens)            |
|----------|---------------------------------------|
| `0`      | Show default layers                   |
| `,`      | Hide default layers                   |
| `1`      | Focus on 1st metal and related vias   |
| `2`      | Focus on 2nd metal and related vias   |
| `3`      | Focus on 3rd metal and related vias   |
| `4`      | Focus on 4th metal and related vias   |
| `5`      | Focus on 5th metal and related vias   |
| `6`      | Focus on 6th metal and related vias   |
| `7`      | Focus on 7th metal and related vias   |
| `8`      | Focus on Gate Poly and related layers |
| `9`      | Focus on Diffusion and related layers |

## Supported PDKs

Currently, we support the following PDKs:
   - `IHP SG13G2`: https://github.com/iic-jku/klayout-layer-shortcuts/blob/main/pdks/ihp-sg13g2.json
   - Skywater `sky130`: https://github.com/iic-jku/klayout-layer-shortcuts/blob/main/pdks/sky130.json
   - Global Foundries `gf180mcu`: https://github.com/iic-jku/klayout-layer-shortcuts/blob/main/pdks/gf180mcu.json

You can add support for additional PDKs by writing a JSON configuration file:
- copy [the existing JSON file](https://github.com/iic-jku/klayout-layer-shortcuts/blob/main/pdks/ihp-sg13g2.json) and ensure the PDK name is volare/ceil compatible
- Noters about the JSON file format
   - NOTE: Layer names must be the same as in the KLayout layer properties XML file (e.g. `~/.volare/ihp-sg13g2/libs.tech/klayout/tech/sg13g2.lyp`)
   - NOTE: The technology name must be the same as in the KLayout technology XML file (e.g. `~/.volare/ihp-sg13g2/libs.tech/klayout/tech/sg13g2.lyt`)
   - NOTE: The layer group names must be unique but are completely custom
- [create a pull request](https://github.com/iic-jku/klayout-layer-shortcuts/compare)_

## Installation using KLayout Package Manager

<a id="installation-instructions"></a>

1. From the main menu, click *Tools*→*Manage Packages* to open the package manager
<p align="center">
<img align="middle" src="doc/klayout-package-manager-install1.jpg" alt="Step 1: Open package manager" width="800"/>
</p>

2. Locate the `Layer Shortcuts`, double-click it to select for installation, then click *Apply*
<p align="center">
<img align="middle" src="doc/klayout-package-manager-install2.jpg" alt="Step 2: Choose and install the package" width="1200"/>
</p>

3. Review and close the package installation report
<p align="center">
<img align="middle" src="doc/klayout-package-manager-install3.jpg" alt="Step 3: Review the package installation report" width="600"/>
</p>

4. Confirm macro execution
<p align="center">
<img align="middle" src="doc/klayout-package-manager-install4.jpg" alt="Step 4: Confirm macro execution" width="500"/>
</p>

