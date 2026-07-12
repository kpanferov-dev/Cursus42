*This project has been created as part of the 42 curriculum by kpanfero.*

## Description

NetPractice is a system administration and networking training project designed to deepen understanding of network configuration and TCP/IP fundamentals. The goal of the project is to solve a series of networking challenges by configuring IP addresses, subnet masks, and routing rules to ensure communication between various devices within simulated network topologies.

The project consists of 10 levels of increasing complexity. Each level presents a partial network configuration that must be completed to enable end-to-end connectivity between all hosts. Through this hands-on approach, students develop practical skills in network design, subnetting, and troubleshooting.

## Instructions

### Prerequisites
- A web browser (Firefox, Chrome, or any modern browser)
- Access to the NetPractice training interface (provided by 42)

### Running the Training Interface
1. Clone this repository to your local machine:
   ```bash
   git clone <repository-url>
   cd netpractice

2. Launch the training interface by running the provided script:
    ```bash
    ./run.sh

3. The interface will open in your default web browser, presenting the network puzzles to solve.

### Saving Your Progress
Each level must be solved and exported as a configuration file. Follow these steps:

- Complete a level in the interface.

- Click the export button to download the configuration file.

- Save the file with the naming convention: levelX (where X is the level number from 1 to 10).

### Submission Requirements
All 10 exported configuration files must be placed at the root of your Git repository. The files should be named exactly:
- level1

- level2

- level3

- level4

- level5

- level6

- level7

- level8

- level9

- level10

No additional compilation or installation steps are required, as the project is entirely browser-based.

### Resources
This project covers essential networking principles, including:

- TCP/IP addressing and subnet masks (IPv4)

- Default gateways and routing tables

- Routers and switches in network topologies

- OSI model layers (particularly Layer 2 and Layer 3)

- Network segmentation and CIDR notation

- ARP and packet forwarding mechanisms

### References and Documentation

RFC 791 – Internet Protocol
https://datatracker.ietf.org/doc/html/rfc791

RFC 950 – Subnet Masking
https://datatracker.ietf.org/doc/html/rfc950

OSI Model Overview – Cloudflare
https://www.cloudflare.com/learning/network-layer/what-is-the-network-layer/

IPv4 Subnetting – Cisco Networking Academy
https://www.cisco.com/c/en/us/support/docs/ip/routing-information-protocol-rip/13788-3.html

NetPractice Tutorials – 42 Network Resources
https://github.com/42Network/netpractice

### Use of AI in This Project

AI tools were consulted during the research phase to clarify networking concepts, provide examples of subnet calculations, and suggest troubleshooting strategies for complex routing issues. No AI-generated code or configuration was used directly; all solutions are the result of independent reasoning and manual configuration.