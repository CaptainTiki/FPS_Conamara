shader_type spatial;
// Interior window glass: faint cyan tint, a little edge sheen.
render_mode blend_mix, cull_disabled, depth_draw_never, specular_schlick_ggx;

uniform vec4 tint : source_color = vec4(0.45, 0.85, 1.0, 0.16);

void fragment() {
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALBEDO = tint.rgb;
	ALPHA = tint.a + fres * 0.25;
	EMISSION = tint.rgb * 0.08;
	ROUGHNESS = 0.05;
	SPECULAR = 0.8;
}
