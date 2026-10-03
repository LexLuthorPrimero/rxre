/* rx550_load - AGENT-22 research instrument
 * PURPOSE: generate REAL, verifiable GPU load headlessly on the RX550 and, in the
 *   same loop, sample the amdgpu power/clock chain, so that
 *   WORKLOAD -> GPU_BUSY -> SCLK/MCLK -> vddgfx -> PPT -> edge TEMP
 *   is measured time-correlated on this target (1002:699f rev c7).
 * HARDWARE SCOPE: selects the AMD EGL device bound to /dev/dri/card1 explicitly;
 *   never by enumeration order. Aborts if that device is not found.
 * READ/WRITE: submits rendering work and READS sysfs only. Writes NO dpm/hwmon
 *   attribute. No force_state, no perf level, no cap change.
 *
 * BUILD: gcc -O2 -o rx550_load rx550_load.c -lEGL -lGLESv2
 * USAGE: rx550_load <seconds> [csv_path]
 *
 * ORACLE (mandatory, see CAVEAT below): every sample does glFinish() +
 * glReadPixels(2x2) and folds the bytes into a checksum. If the render target
 * is dead the checksum never changes and the run reports
 *   ORACLE pixels_changed=0  -> the work was discarded, this is NOT GPU load.
 *
 * CAVEAT / PRIOR FAILURE (measured, do not regress):
 *   Binding EGL_NO_SURFACE leaves the default framebuffer with NO attachments.
 *   Every fragment is discarded, Mesa dead-code-eliminates the fragment shader
 *   and glDrawArrays returns immediately. Measured on this target: 8.4M "fps",
 *   gpu_busy=0%, SCLK pinned 214MHz, PPT at idle 3.2W. That was SUBMISSION
 *   THROUGHPUT, NOT LOAD. Hence the eglCreatePbufferSurface() below.
 */
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>

#define DEV "/sys/class/drm/card1/device"
#define HWM "/sys/class/drm/card1/device/hwmon/hwmon1"

static double now_s(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

/* read a sysfs int; -1 on ANY failure. Never substitutes a default value. */
static long rd(const char *path)
{
	char b[64];
	int fd = open(path, O_RDONLY);
	ssize_t n;
	long v;

	if (fd < 0)
		return -1;
	n = read(fd, b, sizeof(b) - 1);
	close(fd);
	if (n <= 0)
		return -1;
	b[n] = 0;
	return strtol(b, NULL, 10);
}

static const char *FS =
"#version 300 es\n"
"precision highp float;\n"
"uniform float u_t;\n"
"uniform vec2 u_r;\n"
"out vec4 o;\n"
"void main(){\n"
"  vec2 p = gl_FragCoord.xy/u_r*2.0-1.0;\n"
"  float a=0.0;\n"
"  for(int i=0;i<96;i++){\n"
"    a += sin(p.x*float(i)+u_t)*cos(p.y*float(i)-u_t);\n"
"    p = mat2(0.8,0.6,-0.6,0.8)*p*1.03;\n"
"  }\n"
"  o = vec4(vec3(fract(a*0.05)),1.0);\n"
"}\n";

static const char *VS =
"#version 300 es\n"
"void main(){\n"
"  vec2 v[3]=vec2[3](vec2(-1.,-1.),vec2(3.,-1.),vec2(-1.,3.));\n"
"  gl_Position=vec4(v[gl_VertexID],0.,1.);\n"
"}\n";

static GLuint mkprog(const char *vs_src, const char *fs_src)
{
	GLuint v = glCreateShader(GL_VERTEX_SHADER);
	GLuint f = glCreateShader(GL_FRAGMENT_SHADER);
	GLuint p = glCreateProgram();
	GLint ok = 0;
	char l[1024];

	glShaderSource(v, 1, &vs_src, NULL); glCompileShader(v);
	glGetShaderiv(v, GL_COMPILE_STATUS, &ok);
	if (!ok) { glGetShaderInfoLog(v, sizeof l, 0, l);
		fprintf(stderr, "VS_FAIL %s\n", l); return 0; }
	glShaderSource(f, 1, &fs_src, NULL); glCompileShader(f);
	glGetShaderiv(f, GL_COMPILE_STATUS, &ok);
	if (!ok) { glGetShaderInfoLog(f, sizeof l, 0, l);
		fprintf(stderr, "FS_FAIL %s\n", l); return 0; }
	glAttachShader(p, v); glAttachShader(p, f); glLinkProgram(p);
	glGetProgramiv(p, GL_LINK_STATUS, &ok);
	if (!ok) { glGetProgramInfoLog(p, sizeof l, 0, l);
		fprintf(stderr, "LINK_FAIL %s\n", l); return 0; }
	return p;
}

int main(int argc, char **argv)
{
	double secs = (argc > 1) ? atof(argv[1]) : 10.0;
	const char *csv = (argc > 2) ? argv[2] : NULL;
	PFNEGLQUERYDEVICESEXTPROC qd =
		(PFNEGLQUERYDEVICESEXTPROC)eglGetProcAddress("eglQueryDevicesEXT");
	PFNEGLGETPLATFORMDISPLAYEXTPROC gpd =
		(PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
	PFNEGLQUERYDEVICESTRINGEXTPROC qds =
		(PFNEGLQUERYDEVICESTRINGEXTPROC)eglGetProcAddress("eglQueryDeviceStringEXT");
	EGLDeviceEXT devs[16];
	EGLint ndev = 0, i, numcfg, major, minor;
	EGLDisplay dpy = EGL_NO_DISPLAY;
	EGLContext ctx = EGL_NO_CONTEXT;
	EGLSurface surf = EGL_NO_SURFACE;
	EGLConfig cfg;
	EGLint cfgattr[] = { EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
		EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT,
		EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_NONE };
	GLuint prog;
	GLint uloc;
	GLfloat res[2] = { 1280, 720 };
	int chosen = -1;

	if (!qd || !gpd) { fprintf(stderr, "NO_EGL_EXT\n"); return 3; }
	if (!qd(16, devs, &ndev) || ndev <= 0) {
		fprintf(stderr, "NO_EGL_DEVICES\n"); return 3;
	}
	fprintf(stderr, "EGL_DEVICES n=%d\n", ndev);
	for (i = 0; i < ndev; i++) {
		const char *ven = qds(devs[i], EGL_VENDOR);
		const char *drm = qds(devs[i], EGL_DRM_DEVICE_FILE_EXT);
		fprintf(stderr, "EGL_DEV[%d] vendor=%s drm=%s\n", i,
			ven ? ven : "?", drm ? drm : "?");
		/* Mesa reports the CARD node here, not the render node. */
		if (ven && !strcmp(ven, "AMD") &&
		    drm && (strstr(drm, "card1") || strstr(drm, "renderD129")))
			chosen = i;
	}
	if (chosen < 0) { fprintf(stderr, "RX550_EGL_DEVICE_NOT_FOUND\n"); return 4; }
	fprintf(stderr, "CHOSEN dev=%d (RX550 card1)\n", chosen);

	dpy = gpd(EGL_PLATFORM_DEVICE_EXT, devs[chosen], NULL);
	if (dpy == EGL_NO_DISPLAY) { fprintf(stderr, "NO_DISPLAY\n"); return 5; }
	if (!eglInitialize(dpy, &major, &minor)) { fprintf(stderr, "NO_INIT\n"); return 5; }
	if (!eglBindAPI(EGL_OPENGL_ES_API)) { fprintf(stderr, "NO_BINDAPI\n"); return 5; }
	if (!eglChooseConfig(dpy, cfgattr, &cfg, 1, &numcfg) || numcfg < 1) {
		fprintf(stderr, "NO_CONFIG\n"); return 5;
	}
	{
		EGLint ctxattr[] = { EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE };
		ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctxattr);
	}
	if (ctx == EGL_NO_CONTEXT) { fprintf(stderr, "NO_CONTEXT 0x%x\n", eglGetError()); return 5; }

	/* REAL render target. Without this the run is meaningless - see header. */
	{
		EGLint pbattr[] = { EGL_WIDTH, (EGLint)res[0],
			EGL_HEIGHT, (EGLint)res[1], EGL_NONE };
		surf = eglCreatePbufferSurface(dpy, cfg, pbattr);
		if (surf == EGL_NO_SURFACE) {
			fprintf(stderr, "NO_PBUFFER 0x%x\n", eglGetError());
			return 7;
		}
	}
	if (!eglMakeCurrent(dpy, surf, surf, ctx)) {
		fprintf(stderr, "NO_MAKECURRENT 0x%x\n", eglGetError()); return 5;
	}
	{
		const char *r = (const char *)glGetString(GL_RENDERER);
		const char *v = (const char *)glGetString(GL_VENDOR);
		fprintf(stderr, "GL_RENDERER=%s\nGL_VENDOR=%s\n",
			r ? r : "?", v ? v : "?");
	}
	prog = mkprog(VS, FS);
	if (!prog) return 6;
	glUseProgram(prog);
	uloc = glGetUniformLocation(prog, "u_t");
	glUniform2f(glGetUniformLocation(prog, "u_r"), res[0], res[1]);
	glViewport(0, 0, (GLsizei)res[0], (GLsizei)res[1]);

	{
		FILE *f = csv ? fopen(csv, "w") : NULL;
		double t0 = now_s(), tnext = t0;
		long frames = 0;
		unsigned f_last = 0;
		int f_changed = 0;

		if (f)
			fprintf(f, "t_s,gpu_busy,mem_busy,sclk_hz,mclk_hz,vddgfx_mv,"
				   "ppt_uw,edge_mC,pwm,cksum\n");
		printf("# rx550_load secs=%.1f csv=%s\n", secs, csv ? csv : "(none)");
		fflush(stdout);

		while (now_s() - t0 < secs) {
			glUniform1f(uloc, (GLfloat)(now_s() - t0));
			glDrawArrays(GL_TRIANGLES, 0, 3);
			frames++;
			if ((frames & 1023) == 0)
				glFinish();
			if (now_s() >= tnext) {
				double t = now_s();
				unsigned cksum = 0;
				long busy = rd(DEV "/gpu_busy_percent");
				long mbusy = rd(DEV "/mem_busy_percent");
				long sclk = rd(HWM "/freq1_input");
				long mclk = rd(HWM "/freq2_input");
				long vdd = rd(HWM "/in0_input");
				long ppt = rd(HWM "/power1_input");
				long tc = rd(HWM "/temp1_input");
				long pwm = rd(HWM "/pwm1");
				unsigned char px[16];
				int k;

				glFinish();
				glReadPixels(0, 0, 2, 2, GL_RGBA,
					     GL_UNSIGNED_BYTE, px);
				for (k = 0; k < 16; k++)
					cksum = cksum * 31u + px[k];
				if (f_last != cksum)
					f_changed = 1;
				f_last = cksum;

				if (f) {
					fprintf(f, "%.3f,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%u\n",
						t - t0, busy, mbusy, sclk, mclk, vdd, ppt,
						tc, pwm, cksum);
					fflush(f);
				}
				printf("t=%7.3f busy=%3ld%% mbusy=%3ld%% sclk=%9ld "
				       "mclk=%9ld vddgfx=%4ldmV ppt=%9lduW edge=%5ldmC "
				       "pwm=%3ld ck=%08x\n",
					t - t0, busy, mbusy, sclk, mclk, vdd, ppt, tc,
					pwm, cksum);
				fflush(stdout);
				tnext = t + 0.5;
			}
		}
		glFinish();
		printf("# frames=%ld elapsed=%.3fs fps=%.1f\n",
			frames, now_s() - t0, frames / (now_s() - t0));
		printf("# ORACLE pixels_changed=%d  (0 => fragments discarded, NOT real load)\n",
			f_changed);
		if (f)
			fclose(f);
	}
	eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
	eglDestroyContext(dpy, ctx);
	eglTerminate(dpy);
	return 0;
}
