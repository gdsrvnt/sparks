# Hall of fame plaques

Original SVG frames and badge marks acknowledge the people credited in the root README. Pen Badge means intellectual contribution; Onyx Badge means polish through `show-me`. These are sparks acknowledgements, not awards issued by the subjects and not an endorsement.

## Sources and limits

[sources.json](sources.json) records the public GitHub profile, exact avatar URL, retrieval date, original bytes' SHA-256 and image type for each image. The profile URLs and avatar URLs were obtained together from GitHub's public users API. No private photos, inferred identities or generated faces are used. Only circular clipping and placement change how the original images are displayed.

- Lauren Tan: her public **illustrated avatar**, not a photograph.
- Matt Pocock, Brian Madison and Dex: their public GitHub profile images. These are not claimed to be independently authenticated photographs.
- Yann Collet: a text monogram only. His GitHub avatar is an identicon; no portrait has been substituted. A sourced photograph remains open on [issue #85](https://github.com/gdsrvnt/sparks/issues/85).

No image-generation tool was available for this review. The frames and pen/onyx marks are original vector artwork, not photo-generation output. Real photographs for Lauren and Yann and any requested photo-generated finishing remain undone. A contributor can provide a preferred public photo or request removal/replacement of their profile image through #85.

Public availability is not a copyright license. The fetched profile images are not relicensed under this repository's MIT license or their authors' code licenses. No image-specific redistribution grant was found in the GitHub API; rights remain with the image owners. The original frame artwork and renderer are this project's MIT-licensed work. See [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md).

## Rebuild

From the repository root, run `python3 docs/assets/hall-of-fame/render.py` (Python >= 3.11). The stdlib-only renderer checks source hashes and embeds images into self-contained SVGs; it makes no network requests and uses no third-party packages. SVGs carry accessible titles and descriptions. The checked-in source images are retained so rendering does not depend on mutable avatar URLs.

Review the five plaques visually after rebuilding. Test an SVG renderer before publication; plain XML validation alone cannot detect clipped labels or bad portrait placement.
