#ifndef BOOTSTRAP_MANAGER_HPP_INCLUDED
#define BOOTSTRAP_MANAGER_HPP_INCLUDED

#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ip/udp.hpp>
#include <boost/asio/io_service.hpp>
#include <boost/deadline_timer.hpp>


namespace flint{
	using boost::asio::ip::tcp;
	using boost::asio::ip::udp;
	typedef boost::asio::ip::tcp::socket stream_socket;
	typedef boost::asio::ip::address address;
	struct bootstrap_manager
	{
		typedef std::map<address,int> superpeer_map;
		superpeer_map m_superpeers;
		io_service m_io_service;
		boost::asio::strand m_strand;
		boostrap_manager(int listen_port,char const* listen_interface="0.0.0.0");
		listen_on(int listen_port,const char* net_interface);
		void async_accept();
		void open_listen_port();
		void on_incoming_connection();
		void close_connection();
		void allocate_superpeer();
		void add_superpeer();
		bool start_replication();
		~boostrap_manager();
	}
}

#endif
