#include "bootstrap_manager.hpp"
#include <iostream>
#include <string>

int main(int argc,char *argv[])
{
	using namespace flint;
	int port = (argc>1)?std::stoi(argv[1]):6889;
	bootstrap_manager manager(port);
	manager.open_listen_port();
}
