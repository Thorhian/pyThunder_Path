#version 330

uniform sampler2D prev_render;
uniform float cutterRadius;
out vec4 outColor;

ivec4 getBoundingBox(float radius, ivec2 pixelCoords) {
    int top = int(ceil(pixelCoords[1] + radius));
    int bottom = int(floor(pixelCoords[1] - radius));
    int left = int(floor(pixelCoords[0] - radius));
    int right = int(ceil(pixelCoords[0] + radius));

    return ivec4(top, bottom, left, right);
}

void main() {
    ivec2 coords = ivec2(gl_FragCoord.x, gl_FragCoord.y);
    vec4 texColor = texelFetch(prev_render, coords, 0);

    if(texColor.b < 0.1 && texColor.r > 0.99 && texColor.g > 0.49) {
        ivec4 boundingBox = getBoundingBox(cutterRadius, coords);
        texColor.r = 0.0;
        texColor.g = 1.0;
        outColor = texColor;
    }
    else {
        outColor = texColor;
    }
}
