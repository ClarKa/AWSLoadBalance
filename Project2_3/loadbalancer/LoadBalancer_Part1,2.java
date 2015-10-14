import java.io.IOException;
import java.net.ServerSocket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.net.URL;
import java.io.InputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.Reader;

public class LoadBalancer {
	private static final int THREAD_POOL_SIZE = 4;
	private final ServerSocket socket;
	private final DataCenterInstance[] instances;

	public LoadBalancer(ServerSocket socket, DataCenterInstance[] instances) {
		this.socket = socket;
		this.instances = instances;
	}

	// Complete this function
	public void start() throws IOException {
		ExecutorService executorService = Executors.newFixedThreadPool(THREAD_POOL_SIZE);
		int len = instances.length;
		String urlTrailer = ":8080/info/cpu";
		int curr = 0;
		while (true) {
			String urlHeader = instances[curr].getUrl();
			String urlStr = urlHeader + urlTrailer;

			double curr = getCPU(urlStr);
			if (curr > 30.0) {
				double second = getCPU(instances[(curr + 1) % 3].getUrl() + urlTrailer);
				if (second < curr) {
					curr = (curr + 1) % 3;
				}
			}

			Runnable requestHandler = new RequestHandler(socket.accept(), instances[curr]);
			executorService.execute(requestHandler);

			curr = (curr + 1) % 3;
		}
	}

	private static double getCPU(String urlStr) throws IOException {
		String pattern = "(.*)(<body.*?>)(.+?)(</body>)(.*)";
		URL url = new URL(urlStr);
		BufferedReader in = new BufferedReader(new InputStreamReader(url.openStream()));
		String str = in.readLine();
		in.close();
		str = str.replaceAll(pattern,"$3");
		try {
			double curr = Double.parseDouble(str);
			return curr;
		} catch (NumberFormatException e) {
			return -1.0;
		}
	}
}
