import java.io.IOException;
import java.net.ServerSocket;

public class Main {
	private static final int PORT = 80;
	private static DataCenterInstance[] instances;
	private static ServerSocket serverSocket;

	//Update this list with the DNS of your data center instances
	static {
		instances = new DataCenterInstance[3];
		instances[0] = new DataCenterInstance("first_instance", "http://ec2-54-88-205-75.compute-1.amazonaws.com", "i-b77bd663", 1);
		instances[1] = new DataCenterInstance("second_instance", "http://ec2-54-175-241-218.compute-1.amazonaws.com", "i-8177da55", 1);
		instances[2] = new DataCenterInstance("third_instance", "http://ec2-52-23-174-77.compute-1.amazonaws.com", "i-09903ddd", 1);
	}

	public static void main(String[] args) throws IOException {
		initServerSocket();
		LoadBalancer loadBalancer = new LoadBalancer(serverSocket, instances);
		loadBalancer.start();
	}

	/**
	 * Initialize the socket on which the Load Balancer will receive requests from the Load Generator
	 */
	private static void initServerSocket() {
		try {
			serverSocket = new ServerSocket(PORT);
		} catch (IOException e) {
			System.err.println("ERROR: Could not listen on port: " + PORT);
			e.printStackTrace();
			System.exit(-1);
		}
	}
}
