shader_type spatial;
// Flat self-lit colour for FX (tracers, sparks, orbs). energy > 1 feeds the glow.
render_mode unshaded, cull_disabled, shadows_disabled;

uniform vec4 color : source_color = vec4(0.4, 0.95, 1.0, 1.0);
uniform float energy = 3.0;

void fragment() {
	ALBEDO = color.rgb * energy;
}
