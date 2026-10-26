# Daniel Ye — Personal Website

Source for **[danielye.net](https://danielye.net/)**, the academic homepage of **Daniel Ye** (Yifei Ye, 叶逸飞), a Ph.D. candidate in Industrial Engineering at **Iowa State University** (Department of Industrial and Manufacturing Systems Engineering; Center for Nondestructive Evaluation), advised by Dr. Qing Li. His research focuses on modeling and correcting 3D shape deformation in additive manufacturing, with broader interests in 3D deep learning, spatial intelligence, and generative 3D.

- Website: https://danielye.net/
- Google Scholar: https://scholar.google.com/citations?user=viHpZJQAAAAJ
- LinkedIn: https://www.linkedin.com/in/danielye0001/

Both sites are built with **Astro, TypeScript, and Tailwind CSS**.

## Repository layout

| Path | Site | Deployed by |
| --- | --- | --- |
| [`sites/danielye/`](sites/danielye/) | https://danielye.net/ | GitHub Pages, via [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) |
| [`sites/xiaoliang/`](sites/xiaoliang/) | https://xiaoliang.group/ (Xiao Liang's homepage) | Cloudflare Pages, via [`_deploy/xiaoliang-group/`](_deploy/xiaoliang-group/) |

The two sites are independent: each has its own `package.json`, and neither build reads the other's folder.
See each folder's README for how to edit content and build locally.

Other folders: `.github/workflows/indexnow.yml` pings IndexNow (Bing etc.) after each danielye.net deploy;
`_code/` holds research code behind the DeformSolid project page; `_portfolio_dev/` holds older review scripts
from the Jekyll version of the site.

## Acknowledgements

The danielye.net design builds on Yaoyao Liu's [minimal-light](https://github.com/yaoyao-liu/minimal-light) theme (CC0 1.0), which derives from [pages-themes/minimal](https://github.com/pages-themes/minimal) and [orderedlist/minimal](https://github.com/orderedlist/minimal).
