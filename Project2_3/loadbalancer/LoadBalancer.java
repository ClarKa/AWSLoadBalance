import java.io.IOException;
import java.net.ConnectException;
import java.net.ServerSocket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.net.URL;
import java.net.URLConnection;
import java.io.InputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.Reader;
import java.util.List;
import java.util.Properties;

import com.amazonaws.services.ec2.AmazonEC2Client;
import com.amazonaws.services.ec2.model.CreateTagsRequest;
import com.amazonaws.services.ec2.model.DescribeInstancesRequest;
import com.amazonaws.services.ec2.model.DescribeInstancesResult;
import com.amazonaws.services.ec2.model.Instance;
import com.amazonaws.services.ec2.model.Reservation;
import com.amazonaws.services.ec2.model.RunInstancesRequest;
import com.amazonaws.services.ec2.model.RunInstancesResult;
import com.amazonaws.services.ec2.model.Tag;
import com.amazonaws.services.ec2.model.TerminateInstancesRequest;
import com.amazonaws.auth.EnvironmentVariableCredentialsProvider;

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
		int hcTimer = 0;
		int hcInterval = 7;

		//use environmental credentials.
		AmazonEC2Client ec2 = new AmazonEC2Client(new EnvironmentVariableCredentialsProvider());

		AmazonEC2Client ec2 = new AmazonEC2Client(bawsc);

		ec2.setEndpoint("ec2.us-east-1.amazonaws.com");

		while (true) {
			String urlHeader = instances[curr].getUrl();
			String urlStr = urlHeader + urlTrailer;

			if (hcTimer == hcInterval) {

				double currCPU = getCPU(urlStr);
				//Start health check.
				int status = healthCheck(curr);
				instances[curr].status = status;

				System.out.println(instances[curr].status);
				//handle failed health check.
				if (status == -1) {
					System.out.println("failed instances");
					DataCenterInstance newIns = launch(curr, ec2);
					instances[curr] = newIns;
					curr = (curr + 1) % len;
				} else if (status == 0) {
					System.out.println("pending instances");
				}
				//reset health check timer.
				hcTimer = 0;

				//Start checking CPU.
				if (currCPU > 40.0) {
					double nextCPU = getCPU(instances[(curr + 1) % 3].getUrl() + urlTrailer);
					if (nextCPU < currCPU) {
						curr = (curr + 1) % len;
						continue;
					}
				}
			}

			if (instances[curr].status != 1) {
				curr = (curr + 1) % len;
			} else {
				try {
					Runnable requestHandler = new RequestHandler(socket.accept(), instances[curr]);
					executorService.execute(requestHandler);
				} catch (Exception e) {
					if (instances[curr].status == 1) {
						instances[curr].status = -1;
					}
				} finally {
					curr = (curr + 1) % len;
				}
			}
			hcTimer++;
		}
	}

	private double getCPU(String urlStr) throws IOException {
		String pattern = "(.*)(<body.*?>)(.+?)(</body>)(.*)";
		URL url = new URL(urlStr);

		BufferedReader in;
		try {
			in = new BufferedReader(new InputStreamReader(url.openStream()));
		} catch (IOException e) {
			return 101.0;
		}

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

	//return 1 if healthy, return 0 if pending, else return -1
	private int healthCheck (int currIns) throws IOException {
		String load = "/connection/load?id=1505";
		String hcUrl = instances[currIns].getUrl() + load;
		URL url = new URL(instances[currIns].getUrl());
		try {
			URLConnection con = url.openConnection();
			con.setConnectTimeout(500);
			con.setReadTimeout(500);
			con.getInputStream();
			return 1;
		} catch (Exception e) {
			System.out.println("ERRRRrrrrrrr");
			if (instances[currIns].status == 0) {
				return 0;
			} else {
				return -1;
			}
		}
	}

	private DataCenterInstance launch(int currIns, AmazonEC2Client ec2) {
		//terminate failed instance first.
		TerminateInstancesRequest terminateRequest = new TerminateInstancesRequest();
		terminateRequest.withInstanceIds(instances[currIns].getId());
		System.out.println(instances[currIns].getName() + "\t terminating");
		ec2.terminateInstances(terminateRequest);

		//launing new DC.
		RunInstancesRequest runInstancesRequest = new RunInstancesRequest()
	    .withInstanceType("m3.medium")
	    .withImageId("ami-ed80c388")
	    .withMinCount(1)
	    .withMaxCount(1)
	    .withSecurityGroupIds("launch-wizard-1")
	    .withKeyName("15619");

	    RunInstancesResult runInstance = ec2.runInstances(runInstancesRequest);

	    Instance instance = runInstance.getReservation().getInstances().get(0);

	    CreateTagsRequest createTagsRequest = new CreateTagsRequest();
		createTagsRequest
		.withResources(instance.getInstanceId())
		.withTags(new Tag("Project", "2.3"));

		ec2.createTags(createTagsRequest);

		System.out.println("New Data Center Created. Wating to be added into list.");

		//Wait until DNS shows.
		while (instance.getPublicDnsName().isEmpty()) {
				DescribeInstancesRequest describeInstancesRequest = new DescribeInstancesRequest().withInstanceIds(instance.getInstanceId());

				DescribeInstancesResult describeInstance = ec2.describeInstances(describeInstancesRequest);

				List<Reservation> res = describeInstance.getReservations();
				instance = res.get(0).getInstances().get(0);
		}

		String dns = "http://" + instance.getPublicDnsName();

		System.out.println("New data center added into list");
		String name = instances[currIns].getName() + "_I";
		String id = instances[currIns].getId();
		return new DataCenterInstance(name, dns, id, 0);
	}
}
