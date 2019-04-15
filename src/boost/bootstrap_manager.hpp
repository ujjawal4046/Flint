#ifndef BOOTSTRAP_MANAGER_HPP_INCLUDED
#define BOOTSTRAP_MANAGER_HPP_INCLUDED


#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ip/udp.hpp>
#include <boost/asio/io_service.hpp>
#include <boost/thread/recursive_mutex.hpp>
#include <boost/asio.hpp>
#include <boost/weak_ptr.hpp>
#include <boost/bimap.hpp>
#include "socket.hpp"
#include "to_bootstrap_connection.hpp"

#include <vector>

namespace flint{
	struct  bootstrap_manager
	{
		typedef boost::bimap<tcp::endpoint,int> superpeer_map;
		typedef std::map<boost::shared_ptr<stream_socket>,boost::shared_ptr<to_bootstrap_connection>> connection_map;
		static const int MAX_SUPERPEER_ALLOCATION = 3;
		superpeer_map m_superpeers;
		io_service m_io_service;
		connection_map m_connections;
		//boost::asio::strand m_strand;
		int m_listen_port;
		tcp::endpoint m_listen_interface;
		boost::shared_ptr<socket_acceptor> m_listen_socket;
		typedef boost::recursive_mutex mutex_t;
		mutable mutex_t m_mutex;
		bool m_incoming_connection;
		bootstrap_manager(int listen_port,char const* listen_interface="0.0.0.0");
		bool listen_on(int listen_port,const char* net_interface="0.0.0.0");
		void async_accept();
		void open_listen_port();
		void on_incoming_connection(boost::shared_ptr<stream_socket> const& s,boost::weak_ptr<socket_acceptor> const& as,boost::system::error_code const& e);
		void close_connection();
		int allocate_superpeers(std::vector<tcp::endpoint> &buffer);
		void add_superpeer();
		bool start_replication();
		~bootstrap_manager();
	};
}

#endif
