title: Pictures of Shimura curves
status: draft
db: no (new)
waits_on: —
note: >
  New; adapts portrait.modcurve to the quaternionic setting. The shimcurve_pictures table
  (304 rows) is keyed by psl2label. Implementation details (T16 / PrepPictureDataH) should be
  confirmed with the picture author before shipping the "Implementation" paragraph; the
  modcurve pictures were implemented by David Lowry-Duda and the Shimura version is derived
  from that code.
---
For each {{KNOWL('shimcurve','Shimura curve')}} $X_H$ of {{KNOWL('shimcurve.level','level $N$')}}, we visualize the curve through the action of the norm-one unit group of the {{KNOWL('shimcurve.order','order')}} $O$ — a {{KNOWL('group.fuchsian','Fuchsian group')}} $\Gamma\le\operatorname{PSL}_2(\R)$ — on its fundamental domain in the upper half-plane, together with the tessellation induced by the reduction of $H$ modulo $N$. To distinguish translates of the fundamental domain we color it with two separate colors and preserve these colors through translation.

Two Shimura curves whose reductions of $H$ have the same image in the norm-one (Fuchsian) group have the same picture; accordingly, pictures are shared among curves with the same $\mathrm{PSL}_2$-label.

For curves of large {{KNOWL('shimcurve.index','index')}}, only a bounded number of translates of the fundamental domain are drawn, becoming progressively more transparent; the translates shown are chosen to have the largest area in the visualization.
