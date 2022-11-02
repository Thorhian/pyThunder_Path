#version 450 core

layout(local_size_x = 16, local_size_y = 16, local_size_z = 1) in;
layout(rgba32f, binding = 0) uniform sampler2D imageSlice;
layout(rgba32f, binding = 2) uniform sampler2D mask;
layout(std430, binding = 1) buffer counterBuffer
{
  uint counters[];
} cIn;

uniform vec4 color1 = vec4(0.0, 0.0, 0.0, 1.0);

void main() {
  ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
  ivec2 imageDims = imageSize(imageSlice);

  if(texelPosition.x > (imageDims.x - 1) || texelPosition.y > (imageDims.y - 1)) {
    return;
  }

  vec4 imgColor  = imageLoad(imageSlice);

}
