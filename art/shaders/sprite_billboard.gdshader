shader_type spatial;
// Flat sprite enemy: Y-axis billboard, frame strip, emission sheet, hit flash.
render_mode cull_disabled, depth_draw_opaque;

uniform sampler2D albedo_tex : source_color, filter_nearest;
uniform sampler2D emission_tex : source_color, filter_nearest;
uniform int frame = 0;
uniform int frames = 8;
uniform float flash = 0.0;
uniform float emission_energy = 2.5;

void vertex() {
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
		vec4(normalize(cross(vec3(0.0, 1.0, 0.0), INV_VIEW_MATRIX[2].xyz)), 0.0),
		vec4(0.0, 1.0, 0.0, 0.0),
		vec4(normalize(cross(INV_VIEW_MATRIX[0].xyz, vec3(0.0, 1.0, 0.0))), 0.0),
		MODEL_MATRIX[3]);
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec2 uv = vec2((UV.x + float(frame)) / float(frames), UV.y);
	vec4 c = texture(albedo_tex, uv);
	ALPHA = c.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ALBEDO = mix(c.rgb, vec3(1.0, 0.95, 1.0), flash * 0.8);
	EMISSION = texture(emission_tex, uv).rgb * emission_energy + vec3(1.0, 0.5, 0.9) * flash * 0.6;
	ROUGHNESS = 0.9;
	SPECULAR = 0.1;
}
