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
    vec4 tempColor = vec4(1.0, 1.0, 0.0, 1.0);
    bool isProfile = true;

    //TODO: Check for size difference img size due to OpenCV.
    vec4 maskValue = texelFetch(islandMask, coords, 0);

    // FIXME: This will color all stock and non-stock pixels yellow
    // It can never find a true edge pixel since the mask keeps
    // the actual edge pixels out of view of the shader.
    //Return if we are not looking at a pixel in the island
    if (maskValue.r < 0.9) {
        tempColor = sliceColor;
        isProfile = false;
    }

    if (sliceColor.a < 0.9) {
        tempColor = sliceColor;
        isProfile = false;
    }

    int selectedPixel = -1;
    if (isProfile) {
        //Determine if there this is an edge pixel.
        int i = 0;
        for (i = 0; i < 8; i += 1) {
            vec4 sPixel = texelFetch(slice, SCANNER[i] + coords, 0);
            if (sPixel.a < 0.9) {
                selectedPixel = i;
                break;
            }
        }
    }

    //Return if we are not the edge of the island.
    if (selectedPixel < 0) {
        tempColor = sliceColor;
        isProfile = false;
    }

    if (isProfile) {
        //Need to make a vector that goes in the direction of the empty pixel
        vec2 testCoordFloat = vec2(SCANNER[selectedPixel]) * (cutterRadius + spaceAllowance);
        testCoordFloat = testCoordFloat + vec2(coords);
        ivec2 testCoord = ivec2(testCoordFloat);

        ivec4 boundingBox = getBoundingBox(cutterRadius + spaceAllowance, testCoord);

        //Search for solid pixels, return without changing original image if found.
        bool stockFound = false;
        for (int x = boundingBox[2]; x < boundingBox[3]; x += 1) {
            for (int y = boundingBox[0]; y > boundingBox[1]; y -= 1) {
                vec4 current_pix = texelFetch(slice, ivec2(x, y), 0);
                if (current_pix.a > 0.9 && isInsideCircle(cutterRadius, testCoord, ivec2(x, y))) {
                    stockFound = true; //We found stock in out circle
                    //We don't want to label this pixel as a profile edge.
                }
                if (stockFound) break;
            }
            if (stockFound) break;
        }


        if (stockFound) {
            tempColor = sliceColor;
            isProfile = false;
        }

    }

    outColor = tempColor;
}
