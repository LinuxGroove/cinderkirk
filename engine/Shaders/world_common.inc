vec4 WorldFragmentColor ()
{
	vec4 diffuse = texture (diffuse_tex, in_texcoords.xy);
	if (use_alpha_test && diffuse.a < 0.666f)
		discard;

	float lm_multiplier = scaled_lm ? 8.0f : 2.0f;
	vec3  light;

	if (quantize_lm)
	{
		ivec2 lm_size = ivec2 (LMBLOCK_WIDTH, LMBLOCK_HEIGHT);
		vec2  uv_exp = (floor ((lm_size * 16) * in_texcoords.zw) + 0.5) / (lm_size * 16);
		light = texture (lightmap_tex, uv_exp).rgb * lm_multiplier;
	}
	else
		light = texture (lightmap_tex, in_texcoords.zw).rgb * lm_multiplier;

	// Cinderkirk: normal and gloss maps, lit from the direction ericw-tools'
	// light stored for each lightmap sample (s, -t, normal of the texture).
	if (push_constants.bump_scale > 0.0f || push_constants.specular_scale > 0.0f)
	{
		vec4  normal_gloss = texture (normal_tex, in_texcoords.xy);
		vec3  n = normalize (normal_gloss.rgb * 2.0f - 1.0f);
		vec3  l = texture (deluxe_tex, in_texcoords.zw).rgb * 2.0f - 1.0f;
		float l_len = length (l);
		l = l_len > 0.05f ? l / l_len : vec3 (0.0f, 0.0f, 1.0f);
		vec3  lit = light;
		// How much more or less the bump faces the light than the flat face
		// does, so a flat normal changes nothing even in grazing light.
		float bump = (dot (n, l) - l.z) / max (l.z, 0.25f);
		light *= clamp (1.0f + bump * push_constants.bump_scale, 0.0f, 2.5f);

		if (push_constants.specular_scale > 0.0f && normal_gloss.a > 0.004f)
		{
			// The texture's axes on screen, from the derivatives (a cotangent frame).
			vec3  p = in_position;
			vec3  dp1 = dFdx (p), dp2 = dFdy (p);
			vec2  duv1 = dFdx (in_texcoords.xy), duv2 = dFdy (in_texcoords.xy);
			vec3  ng = normalize (cross (dp1, dp2));
			vec3  dp2perp = cross (dp2, ng), dp1perp = cross (ng, dp1);
			vec3  tangent = dp2perp * duv1.x + dp1perp * duv2.x;
			vec3  bitangent = dp2perp * duv1.y + dp1perp * duv2.y;
			float inv = inversesqrt (max (max (dot (tangent, tangent), dot (bitangent, bitangent)), 1e-20f));
			vec3  v = normalize (vec3 (push_constants.view_x, push_constants.view_y, push_constants.view_z) - p);
			vec3  vt = normalize (vec3 (dot (v, tangent) * inv, -dot (v, bitangent) * inv, abs (dot (v, ng))));
			vec3  h = normalize (l + vt);
			float shininess = mix (12.0f, 80.0f, normal_gloss.a);
			float spec = pow (max (dot (n, h), 0.0f), shininess) * normal_gloss.a * step (0.0f, l.z);
			light += lit * spec * push_constants.specular_scale;
		}
	}

	vec4 frag_color;
	frag_color.rgb = diffuse.rgb * light.rgb;

	if (use_fullbright)
	{
		vec3 fullbright = texture (fullbright_tex, in_texcoords.xy).rgb;
		frag_color.rgb += fullbright;
	}

	float fog = exp (-push_constants.fog_density * push_constants.fog_density * in_fog_frag_coord * in_fog_frag_coord);
	fog = clamp (fog, 0.0, 1.0);
	frag_color.rgb = mix (push_constants.fog_color, frag_color.rgb, fog);

	if (use_alpha_blend)
		frag_color.a = push_constants.alpha;

	return frag_color;
}
