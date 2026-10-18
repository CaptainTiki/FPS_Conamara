shader_type spatial;
// Shared kit material: atlas albedo + atlas emission, crunchy nearest filtering.
uniform sampler2D albedo_tex : source_color, filter_nearest_mipmap;
uniform sampler2D emission_tex : source_color, filter_nearest_mipmap;
uniform float emission_energy = 2.0;

void fragment() {
	ALBEDO = texture(albedo_tex, UV).rgb;
	EMISSION = texture(emission_tex, UV).rgb * emission_energy;
	ROUGHNESS = 0.85;
	SPECULAR = 0.25;
}
