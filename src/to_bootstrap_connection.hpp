#ifndef TO_BOOTSTRAP_CONNECTION_HPP_INCLUDED
#define TO_BOOTSTRAP_CONNECTION_HPP_INCLUDED
#include "bootstrap_manager.hpp"
#include "socket.hpp"
#include <vector>

namespace flint{
	struct bootstrap_manager;
	class to_bootstrap_connection{
		public:
		to_bootstrap_connection(bootstrap_manager &man,boost::shared_ptr<stream_socket> s);
		void on_receive_data(const boost::system::error_code &e,std::size_t bytes_transferred);
		private:
		boost::shared_ptr<stream_socket> m_socket;
		bootstrap_manager &m_manager;
		tcp::endpoint m_remote;
		int m_recv_pos;
		std::vector<char> m_recv_buffer;
		void check_remote_type(std::size_t bytes_trans);
	};
}
#endif
