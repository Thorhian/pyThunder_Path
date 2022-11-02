/* # vim: ft=glsl */
#version 450 core

uniform sampler2D slice;
uniform sampler2D islandMask;
uniform float cutterRadius;
uniform float spaceAllowance = 1.0;
out vec4 outColor;

//Coordinates to scan 8 pixels around a central pixel.
const ivec2 SCANNER[] = {ivec2(0, 1),  ivec2(1, 1),
                         ivec2(1, 0),  ivec2(1, -1),
                         ivec2(0, -1), ivec2(-1, -1),
                         ivec2(-1, 0), ivec2(-1, 1)};

ivec4 getBoundingBox(float radius, ivec2 pixelCoords) {
    int top = int(ceil(pixelCoords[1] + radius));
    int bottom = int(floor(pixelCoords[1] - radius));
    int left = int(floor(pixelCoords[0] - radius));
    int right = int(ceil(pixelCoords[0] + radius));

    return ivec4(top, bottom, left, right);
}

bool isInsideCircle(float radius, ivec2 centerCoords, ivec2 pixelCoords) {
    float leftSide = pow(pixelCoords[0] - centerCoords[0], 2) +
        pow(pixelCoords[1] - centerCoords[1], 2);

    return (leftSide < pow(radius, 2));
}

void main() {
    ivec2 coords = ivec2(gl_FragCoord.x, gl_FragCoord.y);
    vec4 sliceColor = texelFetch(slice, coords, 0);
    outColor = vec4(1.0, 1.0, 0.0, 1.0) //Assume this is an profile edge pixel

    //TODO: Check for size difference img size due to OpenCV.
    vec4 maskValue = texelFetch(islandMask, coords, 0);

    //Return if we are not looking at a pixel in the island
    if (maskValue.r < 0.9) {
        return;
    }

    //Determine if there this is an edge pixel.
    int i = 0;
    int selectedPixel = -1;
    for (i = 0; i > 8; i += 1) {
        vec4 sPixel = texelFetch(slice, SCANNER[i], 0);
        if (sPixel.a < 0.9) {
            selectedPixel = i;
            break;
        }
    }

    //Return if we are not the edge of the island.
    if (selectedPixel < 0) {
        return;
    }

    //Need to make a vector that goes in the direction of the empty pixel
    ivec2 testCoord = vec2(SCANNER[selectedPixel]) * (cutterRadius + spaceAllowance);

    ivec4 boundingBox = getBoundingBox(cutterRadius + spaceAllowance, testCoord);
    
    //Search for solid pixels, return without changing original image if found.
    for (int x = boundingBox[2]; x < boundingBox[3]; x += 1) {
        for (int y = boundingBox[0]; y > boundingBox[1]; y -= 1) {
            vec4 current_pix = texelFetch(slice, ivec2(x, y));
            if (current_pix.a > 0.9 && isInsideCircle(cutterRadius, testCoord, ivec(x, y))) {
                outColor = sliceColor; //We found stock in out circle
                return; //Wer don't want to label this pixel as a profile edge.
            }
        }
    }

    return; //Should only arrive here if this is a viable profifle edge pixel
}
