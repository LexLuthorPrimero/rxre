/* ###
 * RXRE-BMS-EXT-003. Post-script de Ghidra para `binary.decompile`.
 *
 * POR QUE ESTE FICHERO EXISTE
 * ---------------------------
 * `binary.decompile` figuraba en el registry del proyecto y sus pruebas
 * PASABAN, pero solo en modo fixture: `fixture_json` salta el bloque que
 * ejecuta Ghidra. El script que faltaba (`DumpDecomp.java`) no estaba en el
 * arbol, asi que la capacidad no se habia ejecutado nunca contra un binario
 * real. Ver `tools/rxre/backends/adapters/gh_decompile.py`.
 *
 * QUE EMITE, Y POR QUE ESTA FORMA
 * -------------------------------
 * Un JSON con esta forma EXACTA, que es la que el adapter parsea:
 *
 *   {
 *     "producer": "ghidra-decompiler",
 *     "program":  "<nombre del programa>",
 *     "n_functions_total": <int>,
 *     "decompiladas": <int>,
 *     "aviso": "<texto libre: por que hay 0, si lo hay>",
 *     "functions": [
 *       { "name", "address", "size", "nparams",
 *         "calling_convention", "decompiled": <bool>,
 *         "c": "<pseudocodigo>", "error": "<motivo si fallo>" }
 *     ]
 *   }
 *
 * Si el JSON no aparece, el adapter responde "el script no escribio el JSON",
 * que es un fallo de producer y no una entrada sin funciones. Por eso el
 * script escribe SIEMPRE el fichero, incluso cuando no encuentra nada: un
 * `empty` y un `crash` tienen que ser distinguibles desde fuera.
 *
 * SIN INVENTAR NADA
 * -----------------
 * Cada clase y cada metodo usados aqui se han verificado con `javap` contra
 * los JARs instalados en /usr/lib64/ghidra, no de memoria:
 *
 *   ghidra.app.script.GhidraScript        Base.jar
 *   ghidra.app.decompiler.DecompInterface  Decompiler.jar
 *   ghidra.app.decompiler.DecompileOptions Decompiler.jar
 *   ghidra.app.decompiler.DecompileResults Decompiler.jar
 *   ghidra.program.model.listing.Function  SoftwareModeling.jar
 *   ghidra.util.task.TaskMonitor          Utility.jar
 *
 * La forma del script (extends GhidraScript, run(), getScriptArgs(),
 * openProgram(currentProgram), decompileFunction(f, t, monitor), dispose())
 * esta tomada de un script que Ghidra instala:
 *   Ghidra/Features/BSim/ghidra_scripts/DumpBSimSignaturesScript.java
 *
 * LIMITACIONES QUE EL PROPIO SCRIPT DECLARA
 * ------------------------------------------
 * Una decompilacion es una REPRESENTACION recuperada de forma automatica:
 * Ghidra infiere tipos, parametros y control de flujo que el binario no
 * declara, y los nombres (`FUN_00100360`) son heuristicos. Este script
 * escribe lo que el decompilador devuelve, y nada mas.
 */
//@category RXRE

import java.io.File;
import java.io.OutputStreamWriter;
import java.io.FileOutputStream;
import java.io.BufferedWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.util.task.TaskMonitor;

public class DumpDecomp extends GhidraScript {

	/** Segundos por funcion. El adapter pasa un timeout global; este es el
	 *  tope por funcion para que una sola no se coma el presupuesto entero. */
	private static final int TIMEOUT_POR_FUNCION = 120;

	@Override
	public void run() throws Exception {
		String[] args = getScriptArgs();
		File salida = null;
		int maxFuncs = 5;
		String filtro = "";

		// --- ARGS: se validan ANTES de tocar el decompilador. Un producer
		// que no sabe a donde escribir no debe gastar minutos de JVM.
		if (args != null && args.length > 0 && args[0] != null
				&& args[0].trim().length() > 0) {
			salida = new File(args[0].trim());
		}
		if (args != null && args.length > 1 && args[1] != null
				&& args[1].trim().length() > 0) {
			try {
				maxFuncs = Integer.parseInt(args[1].trim());
			}
			catch (NumberFormatException e) {
				println("DumpDecomp: max_funcs no es un entero: '" + args[1]
						+ "'; se usa 5");
				maxFuncs = 5;
			}
		}
		if (args != null && args.length > 2 && args[2] != null) {
			filtro = args[2].trim();
		}

		if (salida == null) {
			println("DumpDecomp ERROR: falta el primer argumento, que es la "
					+ "ruta del JSON de salida. No se puede producir artefacto.");
			return;
		}

		if (maxFuncs <= 0) {
			println("DumpDecomp: max_funcs=" + maxFuncs + " no tiene sentido; "
					+ "se usa 1");
			maxFuncs = 1;
		}

		DecompInterface decomp = new DecompInterface();
		StringBuilder json = new StringBuilder();
		int total = 0;
		int decompiladas = 0;
		StringBuilder avisos = new StringBuilder();

		try {
			decomp.setOptions(new DecompileOptions());
			// El pseudocodigo C es lo que el adapter guarda; el arbol de
			// sintaxis solo se usa para otras cosas y aqui no aporta.
			decomp.toggleCCode(true);
			decomp.toggleSyntaxTree(false);

			if (!decomp.openProgram(currentProgram)) {
				avisos.append("openProgram() devolvio false: ")
						.append(decomp.getLastMessage() == null
								? "(sin mensaje)" : decomp.getLastMessage())
						.append(" | ");
				escribir(salida, construir(currentProgram, json, total,
						decompiladas, avisos.toString()));
				return;
			}

			List<Function> candidatas = new ArrayList<Function>();
			FunctionIterator it = currentProgram.getFunctionManager()
					.getFunctions(true);
			while (it.hasNext()) {
				Function f = it.next();
				if (f.isExternal() || f.isThunk()) {
					continue;
				}
				String nombre = f.getName();
				if (filtro.length() > 0 && nombre != null
						&& !nombre.toLowerCase().contains(filtro.toLowerCase())) {
					continue;
				}
				candidatas.add(f);
			}
			total = candidatas.size();

			// MEDIDO: el adapter por defecto pide las MAS GRANDES, porque
			// una funcion grande es la que mas seudo-tiene y la que mas
			// demuestra que el decompilador esta trabajando. Sin esto,
			// `max_funcs=5` sobre un binario enorme devuelve cinco stubs de
			// una linea y no prueba nada.
			java.util.Collections.sort(candidatas,
					new java.util.Comparator<Function>() {
						@Override
						public int compare(Function a, Function b) {
							long sa = tamano(a);
							long sb = tamano(b);
							if (sa != sb) {
								return sa < sb ? 1 : -1;   // mayor primero
							}
							return a.getName().compareTo(b.getName());
						}
						private long tamano(Function f) {
							try {
								if (f.getBody() == null) {
									return 0;
								}
								return f.getBody().getNumAddresses();
							}
							catch (Exception e) {
								return 0;
							}
						}
					});

			json.append("[\n");
			boolean primero = true;
			int tomadas = 0;
			for (Iterator<Function> ci = candidatas.iterator();
					ci.hasNext() && tomadas < maxFuncs; ci.next()) {
				Function f = ci.next();
				tomadas++;
				if (!primero) {
					json.append(",\n");
				}
				primero = false;
				// MEDIDO (esta iteracion): contar las "decompiled":true
				// buscando el texto en el JSON montado miente, porque el
				// pseudocodigo es TEXTO de C y puede contener esa cadena
				// literally. El contador sale de la misma operacion que
				// decide si la funcion se descompilo.
				boolean ok = objeto(f, decomp, json);
				if (ok) {
					decompiladas++;
				}
			}
			json.append("\n]\n");

			escribir(salida, construir(currentProgram, json, total,
					decompiladas, avisos.toString()));
		}
		catch (Throwable t) {
			// Un producer que revienta sin escribir nada es indistinguible de
			// uno que no ha corrido. Se escribe el JSON de todas formas, con
			// el error dentro, para que el lado pueda leerlo.
			avisos.append("excepcion en el script: ")
					.append(t.getClass().getName()).append(": ")
					.append(String.valueOf(t.getMessage())).append(" | ");
			try {
				escribir(salida, construir(currentProgram, json, total,
						decompiladas, avisos.toString()));
			}
			catch (Throwable t2) {
				println("DumpDecomp: no se pudo escribir ni el error: " + t2);
			}
		}
		finally {
			try {
				decomp.dispose();
			}
			catch (Throwable t) {
				// dispose() falla raramente; no debe impedir el resultado.
			}
		}
	}

	/** Decompila UNA funcion y ANADE su objeto JSON a `destino`.

	 *  Devuelve `true` si el decompilador produjo pseudocodigo. El contador
	 *  de "decompiladas" sale de aqui y no de buscar texto en el JSON. */
	private boolean objeto(Function f, DecompInterface decomp,
			StringBuilder destino) {
		StringBuilder b = new StringBuilder();
		b.append("{");
		b.append("\"name\":").append(cadena(f.getName()));
		b.append(",\"address\":").append(cadena(direccion(f.getEntryPoint())));
		b.append(",\"size\":").append(tamanoSeguro(f));
		b.append(",\"nparams\":").append(f.getParameterCount());
		b.append(",\"calling_convention\":")
				.append(cadena(f.getCallingConventionName()));

		boolean ok = false;
		StringBuilder pseudo = new StringBuilder();
		String error = null;
		try {
			DecompileResults r = decomp.decompileFunction(f,
					TIMEOUT_POR_FUNCION, TaskMonitor.DUMMY);
			if (r != null && r.decompileCompleted()
					&& r.getDecompiledFunction() != null) {
				String c = r.getDecompiledFunction().getC();
				if (c != null) {
					pseudo.append(c);
					ok = pseudo.length() > 0;
				}
			}
			if (!ok && r != null) {
				error = r.getErrorMessage() == null
						? "decompileCompleted() falso" : r.getErrorMessage();
			}
			else if (!ok) {
				error = "decompileFunction() devolvio null";
			}
		}
		catch (Throwable t) {
			error = t.getClass().getName() + ": " + String.valueOf(t.getMessage());
		}

		b.append(",\"decompiled\":").append(ok);
		b.append(",\"c\":").append(cadena(pseudo.toString()));
		b.append(",\"error\":").append(error == null ? "null" : cadena(error));
		b.append("}");
		destino.append(b.toString());
		return ok;
	}


	/** Envuelve la lista de funciones en el JSON que el adapter espera. */
	private String construir(Object programa, StringBuilder json, int total,
			int decompiladas, String avisos) {
		return "{\n"
				+ "  \"producer\": \"ghidra-decompiler\",\n"
				+ "  \"program\": " + cadena(String.valueOf(programa)) + ",\n"
				+ "  \"n_functions_total\": " + total + ",\n"
				+ "  \"decompiladas\": " + decompiladas + ",\n"
				+ "  \"aviso\": " + cadena(avisos == null ? "" : avisos) + ",\n"
				+ "  \"functions\": " + (json.length() == 0 ? "[]" : json.toString())
				+ "\n}\n";
	}

	/** Escritura ATOMICA: temporal + rename. Un JSON a medias es peor que
	 *  ninguno: el adapter lo parsearia y creeria que hay funciones. */
	private void escribir(File destino, String contenido) throws Exception {
		File dir = destino.getParentFile();
		if (dir != null && !dir.exists()) {
			dir.mkdirs();
		}
		File tmp = new File(destino.getAbsolutePath() + ".tmp");
		OutputStreamWriter w = new OutputStreamWriter(
				new FileOutputStream(tmp), StandardCharsets.UTF_8);
		try {
			BufferedWriter bw = new BufferedWriter(w);
			bw.write(contenido);
			bw.flush();
		}
		finally {
			w.close();
		}
		if (!tmp.renameTo(destino)) {
			// renameTo falla si el destino existe en algunos sistemas de
			// ficheros. Se borra y se reintenta una vez.
			destino.delete();
			if (!tmp.renameTo(destino)) {
				throw new Exception("no se pudo renombrar " + tmp + " a " + destino);
			}
		}
	}

	private long tamanoSeguro(Function f) {
		try {
			return f.getBody() == null ? 0 : f.getBody().getNumAddresses();
		}
		catch (Exception e) {
			return 0;
		}
	}

	private String direccion(Address a) {
		return a == null ? "" : a.toString();
	}

	/** Cadena JSON escapada. El pseudocodigo de Ghidra lleva comillas y
	 *  saltos de linea; sin esto el JSON no parsea. */
	private String cadena(String s) {
		if (s == null) {
			return "null";
		}
		StringBuilder b = new StringBuilder(s.length() + 16);
		b.append('"');
		for (int i = 0; i < s.length(); i++) {
			char ch = s.charAt(i);
			switch (ch) {
				case '"':
					b.append("\\\"");
					break;
				case '\\':
					b.append("\\\\");
					break;
				case '\n':
					b.append("\\n");
					break;
				case '\r':
					b.append("\\r");
					break;
				case '\t':
					b.append("\\t");
					break;
				case '\b':
					b.append("\\b");
					break;
				case '\f':
					b.append("\\f");
					break;
				default:
					if (ch < 0x20) {
						b.append(String.format("\\u%04x", (int) ch));
					}
					else {
						b.append(ch);
					}
			}
		}
		b.append('"');
		return b.toString();
	}
}