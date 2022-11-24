/* # vim: ft=glsl */
#version 330 core

uniform sampler2D imageSlice;
uniform sampler2D mask;
uniform float circleRadius;

#define PI 3.1415926538
#define PROX 2.0

out vec4 outColor;

bool isInsideCircle(float radius, vec2 centerCoords, ivec2 pixelCoords) {
    float leftSide = pow(pixelCoords.x - centerCoords.x, 2) +
        pow(pixelCoords.y - centerCoords.y, 2);

    return (leftSide < pow(radius, 2));
}

ivec4 getBoundingBox(float radius, ivec2 pixelCoords) {
    int top = int(ceil(pixelCoords[1] + radius));
    int bottom = int(floor(pixelCoords[1] - radius));
    int left = int(floor(pixelCoords[0] - radius));
    int right = int(ceil(pixelCoords[0] + radius));

    return ivec4(top, bottom, left, right);
}

void main() {
    ivec2 pixelCoords = ivec2(gl_FragCoord.xy);
    vec4 sliceColor = texelFetch(imageSlice, pixelCoords, 0);

    vec4 tempColor = vec4(0.0, 0.0, 0.0, 0.0);

    ivec4 boundingBox = getBoundingBox(circleRadius, pixelCoords);
    bool isDone = false;
    if (sliceColor.a < 0.1) {
        for(int x = boundingBox[2]; x < boundingBox[3]; x += 1) {
            for(int y = boundingBox[0]; y > boundingBox[1]; y -= 1) {
                vec4 currentPix = texelFetch(imageSlice, ivec2(x, y), 0);
                ivec2 currentCoords = ivec2(x, y);

                if (isInsideCircle(circleRadius, pixelCoords, currentCoords)
                    && currentPix.a > 0.9) {

                    isDone = true;
                    break;
                }
                /*
                if (isInsideCircle(circleRadius, pixelCoords, currentCoords)
                    && currentPix.a > 0.9) {
                    isDone = true;
                    break;
                }


                if (maskValue > 0.9 && currentPix.b < 0.1) {
                    break;
                }*/

                /*if (
                    currentPix.a > 0.9 &&
                    currentPix.b < 0.1 &&
                    (currentPix.r < 0.1 && currentPix.g < 0.1) &&
                    !isInsideCircle(circleRadius, pixelCoords, currentCoords)
                ) {
                    if (isInsideCircle(circleRadius, pixelCoords, currentCoords)) {

                    }
                    bool isGoldilocks = isInsideCircle(circleRadius + PROX_TOLERANCE,
                                                       pixelCoords, currentCoords);
                    if (!isGoldilocks) {
                        tempColor = vec4(0.0, 0.0, 1.0, 1.0);
                        break;
                    }
                }*/

            }
            if (isDone) {
                break;
            }
        }
    } else {
        isDone = true;
    }

    if (!isDone) {
        for(int x = boundingBox[2]; x < boundingBox[3]; x += 1) {
            for(int y = boundingBox[0]; y > boundingBox[1]; y -= 1) {

                vec4 currentPix = texelFetch(imageSlice, ivec2(x, y), 0);
                ivec2 currentCoords = ivec2(x, y);
                float maskValue = texelFetch(mask, currentCoords, 0).r;

                if (isInsideCircle(circleRadius + PROX, pixelCoords, currentCoords) && 
                    currentPix.a > 0.9 &&
                    maskValue > 0.9) {

                    ivec2 direction = pixelCoords - currentCoords;
                    
                    float theta = atan(direction.x / direction.y);
                    if (direction.x < 0) {
                        theta = theta + PI;
                    }
                    theta = theta / (PI * 2);
                    tempColor = vec4(0.0, theta, 0.0, 1.0);
                    break;
                }

            }
        }
    }

        outColor = tempColor;
}
