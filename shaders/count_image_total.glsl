#version 450 core

layout(local_size_x = 16, local_size_y = 16, local_size_z = 1) in;
layout(binding = 0) uniform sampler2D imageSlice;
layout(binding = 2) uniform sampler2D mask;
layout(std430, binding = 2) buffer counterBuffer
{
  uint counters[];
} cIn;

uniform vec4 color1 = vec4(0.0, 0.0, 0.0, 1.0);
uniform vec4 color2 = vec4(0.0, 0.0, 1.0, 1.0);
uniform vec4 color3 = vec4(0.0, 1.0, 0.0, 1.0);
uniform bool useMask = false;

void main() {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 imageDims = textureSize(imageSlice, 0);

    if (pos.x > (imageDims.x - 1) || pos.y > (imageDims.y - 1)) {
        return;
    }

    if (useMask) {
        vec4 maskValue = texelFetch(mask, pos, 0);
        if (maskValue.r < 0.9) {
            return;
        }
    }

    vec4 texColor = texelFetch(imageSlice, pos, 0);
    atomicAdd(cIn.counters[4], 1); //Total Pixels

    if (texColor.a > 0.9) {
        if (texColor.b > 0.9) {
            atomicAdd(cIn.counters[0], 1);
            return;
        }
        if (texColor.g > 0.9 && texColor.r < 0.1) {
            atomicAdd(cIn.counters[1], 1);
            return;
        }
        if (texColor.r > 0.9 && texColor.g < 0.1) {
            atomicAdd(cIn.counters[2], 1);
            return;
        }

        atomicAdd(cIn.counters[3], 1);
    }
}
