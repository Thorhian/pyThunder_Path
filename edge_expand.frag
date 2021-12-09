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

bool searchForBorder(float radius, ivec4 boundingBox) {
    for(int x = boundingBox[2]; x < boundingBox[3]; x += 1) {
        for(int y = boundingBox[0]; y > boundingBox[1]; y -= 1) {
            vec4 current_pix = texelFetch(prev_render, ivec2(x, y), 0);

            if(!(current_pix.b > 0.98) && current_pix.r > 0.95 && current_pix.g > 0.45) {
                return true;
            }
        }
    }
    return false;
}

void main() {
    ivec2 coords = ivec2(gl_FragCoord.x, gl_FragCoord.y);
    vec4 texColor = texelFetch(prev_render, coords, 0);

    if(texColor.b < 0.1) {
        ivec4 boundingBox = getBoundingBox(cutterRadius, coords);
        if(searchForBorder(cutterRadius, boundingBox)) {
            outColor = vec4(0.0, 1.0, 0.0, 1.0);
        }
        else {
            outColor = texColor;
        }
    }
    else {
        outColor = texColor;
    }
}
