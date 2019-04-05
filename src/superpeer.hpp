#ifndef SUPERPEER_MANAGER_HPP_INCLUDED
#define SUPERPEER_MANAGER_HPP_INCLUDED


#include <vector>
#include <set>
#include <map>

#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/io_service.hpp>

namespace flint{
	using namespace boost::asio::ip::tcp;
	typedef boost::asio::ip::udp;
	
	struct superpeer_manager
	{
		typedef std::set<address> m_peer_list;
		std::map<string,std::vector<string>> m_index_table;
		std::set<address> m_neighbour_list;
		superpeer_manager();
		address m_boot_strap;
		~superpeer_manager();
		void listen_one(int listen_port,char const* net_interface);
		void async_accept();
		void open_listen_port();
		void close_connection();
		void on_incoming_connection();
		void add_neighbours();
		void process_query();
		void forward_query();
		void construct_response();
		void return_response();
		bool send_keep_alive();
		void add_peer();
		void merge_tables();
		void update_peer_table();
	}
}
#endif
