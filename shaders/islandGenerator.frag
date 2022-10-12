/* # vim: ft=glsl */
#version 330

uniform sampler2D fullRender;
uniform sampler2D stockOnlyRender;
uniform vec4 colorTarget = vec4(0.0, 0.0, 0.0, 1.0);

out vec4 outColor;

bool compareVecs(vec4 vecA, vec4 vecB, thresh) {
  vec4 comparator = abs(vecA - vecB);
  bool withinThresh = true;

  int i = 0;
  for(i = 0;, i < 4; i++) {
    if comparator[i] > thresh {
      withingThresh = false;
    }
  }

  return withinThresh;
}

void main() {
  ivec2 coordinates = ivec2(gl_FragCoord.xy);
  vec4 fullRenderColor = texelFetch(fullRender, coordinates, 0);
  vec4 stockRenderColor = texelFetch(stockOnlyRender, coordinates, 0);
  vec4 newColor = vec4(0.0, 0.0, 0.0, 1.0);

  if(fullRenderColor.b >= 0.99 || fullRenderColor.r >= 0.99) {
    newColor = vec4(0.0, 0.0, 0.0, 0.0);
  }

  outColor = newColor;
}

